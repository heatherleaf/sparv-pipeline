"""Util functions for Snakefile."""

import copy
import inspect
import os
import re
from collections import defaultdict, OrderedDict
from itertools import combinations
from pathlib import Path
from typing import List, Set, Tuple

import snakemake
from snakemake.io import expand

from sparv import util
from sparv.core import config as sparv_config
from sparv.core import paths, registry, log_handler
from sparv.util.classes import (AllDocuments, Annotation, Binary, Config, Corpus, Document, Export, ExportAnnotations,
                                ExportInput, Language, Model, ModelOutput, Output, Source)


class SnakeStorage(object):
    """Object to store variables involving all rules."""

    def __init__(self):
        """Init attributes."""
        # All output annotations available, used for printing a list
        self.all_annotations = {}

        # All named targets available, used in list_targets
        self.named_targets = []
        self.export_targets = []
        self.install_targets = []
        self.model_targets = []
        self.custom_targets = []

        self.model_outputs = []  # Outputs from modelbuilders, used in build_models
        self.install_outputs = defaultdict(list)  # Outputs from all installers, used in install_annotated_corpus
        self.source_files = []  # List which will contain all source files
        self.all_rules: List[RuleStorage] = []  # List containing all rules created
        self.ordered_rules = []  # List of rules containing rule order


class RuleStorage(object):
    """Object to store parameters for a snake rule."""

    def __init__(self, module_name, f_name, annotator_info):
        """Init attributes."""
        self.module_name = module_name
        self.f_name = f_name
        self.annotator_info = annotator_info
        self.target_name = f"{module_name}:{f_name}"  # Rule name for the "all-files-rule" based on this rule
        self.rule_name = f"{module_name}::{f_name}"  # Actual Snakemake rule name for internal use
        self.full_name = f"{module_name}:{f_name}"  # Used in messages to the user
        self.inputs = []
        self.outputs = []
        self.parameters = {}
        self.docs = []  # List of parameters referring to Document
        self.doc_annotations = []  # List of parameters containing the {doc} wildcard
        self.wildcard_annotations = []  # List of parameters containing other wildcards
        self.missing_config = set()
        self.exit_message = None

        self.type = annotator_info["type"].name
        self.annotator = annotator_info["type"] is registry.Annotator.annotator
        self.importer = annotator_info["type"] is registry.Annotator.importer
        self.exporter = annotator_info["type"] is registry.Annotator.exporter
        self.installer = annotator_info["type"] is registry.Annotator.installer
        self.modelbuilder = annotator_info["type"] is registry.Annotator.modelbuilder
        self.description = annotator_info["description"]
        self.source_type = annotator_info["source_type"]
        self.import_outputs = annotator_info["outputs"]
        self.order = annotator_info["order"]


def rule_helper(rule: RuleStorage, config: dict, storage: SnakeStorage, config_missing: bool = False,
                custom_rule_obj: dict = None) -> bool:
    """
    Populate rule with Snakemake input, output and parameter list.

    Return True if a Snakemake rule should be created.
    """
    if config.get("debug"):
        print()
        print("{}{}:{} {}".format(util.Color.BOLD, rule.module_name.upper(), util.Color.RESET, rule.f_name))
        print()

    # Only create certain rules when config is missing
    if config_missing and not rule.modelbuilder:
        return False

    # Skip any annotator that is not available for the selected corpus language
    if rule.annotator_info["language"] and sparv_config.get("metadata.language") not in rule.annotator_info["language"]:
        return False

    if rule.importer:
        rule.inputs.append(Path(get_source_path(), "{doc}." + rule.source_type))
        if rule.source_type == sparv_config.get("source_type", "xml"):
            # Exports always generate corpus text file
            rule.outputs.append(paths.annotation_dir / "{doc}" / util.TEXT_FILE)
            # If importer guarantees other outputs, add them to outputs list
            if rule.import_outputs:
                if isinstance(rule.import_outputs, Config):
                    rule.import_outputs = sparv_config.get(rule.import_outputs, rule.import_outputs.default)
                annotations_ = set()
                for annotation in rule.import_outputs:
                    annotations_.add(annotation)
                    annotations_.add(util.split_annotation(annotation)[0])
                for element in annotations_:
                    rule.outputs.append(paths.annotation_dir / get_annotation_path(element))

    params = OrderedDict(inspect.signature(rule.annotator_info["function"]).parameters)
    output_dirs = set()

    if custom_rule_obj:
        if custom_rule_obj.get("output") or custom_rule_obj.get("params"):
            populate_custom_rule(rule, params, storage, custom_rule_obj)
        else:
            # This rule has already been populated, so don't process it again
            return False
    else:
        if missing_defaults(params, rule) is not None:
            # This is probably an unused custom rule, so don't process it
            storage.custom_targets.append((rule.target_name, rule.description))
            return False

    # Go though function parameters and handle based on type
    for param_name, param in params.items():
        # Output
        if isinstance(param.default, Output):
            param_value, missing_configs = registry.expand_variables(param.default, rule.full_name)
            rule.missing_config.update(missing_configs)
            ann_path = get_annotation_path(param_value, data=param.default.data, common=param.default.common)
            if param.default.all_docs:
                rule.outputs.extend(map(Path, expand(escape_wildcards(paths.annotation_dir / ann_path),
                                                     doc=get_source_files(storage.source_files))))
            elif param.default.common:
                rule.outputs.append(paths.annotation_dir / ann_path)
                if rule.installer:
                    storage.install_outputs[rule.target_name].append(paths.annotation_dir / ann_path)
            else:
                rule.outputs.append(get_annotation_path(param_value, data=param.default.data))
            rule.parameters[param_name] = param_value
            if "{" in param_value:
                rule.wildcard_annotations.append(param_name)
            storage.all_annotations.setdefault(rule.module_name, {}).setdefault(rule.f_name,
                                                                                {"description": rule.description,
                                                                                 "annotations": []})
            storage.all_annotations[rule.module_name][rule.f_name]["annotations"].append((param.default,
                                                                                          param.default.description))
        # ModelOutput
        elif isinstance(param.default, ModelOutput):
            param_value, missing_configs = registry.expand_variables(param.default, rule.full_name)
            rule.missing_config.update(missing_configs)
            model = util.get_model_path(param_value)
            rule.outputs.append(model)
            rule.parameters[param_name] = str(model)
            storage.model_outputs.append(model)
        # Annotation
        elif registry.dig(Annotation, param.default):
            param_value, missing_configs = registry.expand_variables(param.default, rule.full_name)
            rule.missing_config.update(missing_configs)
            ann_path = get_annotation_path(param_value, data=param.default.data, common=param.default.common)
            if rule.exporter or rule.installer or param.default.all_docs:
                if param.default.all_docs:
                    rule.inputs.extend(expand(escape_wildcards(paths.annotation_dir / ann_path),
                                              doc=get_source_files(storage.source_files)))
                else:
                    rule.inputs.append(paths.annotation_dir / ann_path)
            elif param.default.common:
                rule.inputs.append(paths.annotation_dir / ann_path)
            else:
                rule.inputs.append(ann_path)

            rule.parameters[param_name] = param_value
            if "{" in param_value:
                rule.wildcard_annotations.append(param_name)
        # ExportAnnotations
        elif param.default == ExportAnnotations or isinstance(param.default, ExportAnnotations):
            export_type = param.default.export_type
            rule.parameters[param_name] = []
            export_annotations = sparv_config.get(f"{export_type}.annotations", [])
            for annotation in export_annotations:
                annotation, _, new_name = annotation.partition(" as ")
                param_value, missing_configs = registry.expand_variables(annotation, rule.full_name)
                rule.missing_config.update(missing_configs)
                if param.default.is_input:
                    rule.inputs.append(paths.annotation_dir / get_annotation_path(param_value))
                if new_name:
                    param_value = " as ".join((param_value, new_name))
                rule.parameters[param_name].append(param_value)
        # Corpus
        elif param.default == Corpus or isinstance(param.default, Corpus):
            rule.parameters[param_name] = sparv_config.get("metadata.id")
        # Language
        elif param.default == Language or isinstance(param.default, Language):
            rule.parameters[param_name] = sparv_config.get("metadata.language")
        # Document
        elif param.default == Document or isinstance(param.default, Document):
            rule.docs.append(param_name)
        # AllDocuments (all source documents)
        elif registry.dig(AllDocuments, param.default):
            rule.parameters[param_name] = get_source_files(storage.source_files)
        # Model
        elif registry.dig(Model, param.default):
            if param.default is not None:
                if isinstance(param.default, Model):
                    param_value, missing_configs = registry.expand_variables(param.default, rule.full_name)
                    rule.missing_config.update(missing_configs)
                    model = util.get_model_path(param_value)
                    rule.inputs.append(model)
                    rule.parameters[param_name] = str(model)
                elif isinstance(param.default, (list, tuple)):
                    rule.parameters[param_name] = []
                    for model in param.default:
                        param_value, missing_configs = registry.expand_variables(model, rule.full_name)
                        rule.missing_config.update(missing_configs)
                        model = util.get_model_path(param_value)
                        rule.inputs.append(model)
                        rule.parameters[param_name].append(str(model))
        # Binary
        elif isinstance(param.default, Binary):
            param_value, missing_configs = registry.expand_variables(param.default, rule.full_name)
            rule.missing_config.update(missing_configs)
            binary = paths.get_bin_path(param_value)
            rule.inputs.append(binary)
            rule.parameters[param_name] = str(binary)
        # Source
        elif param.default == Source or isinstance(param.default, Source):
            rule.parameters[param_name] = get_source_path()
        # Export
        elif param.default == Export or isinstance(param.default, Export):
            param_value, missing_configs = registry.expand_variables(param.default, rule.full_name)
            rule.missing_config.update(missing_configs)
            if param.default.absolute_path:
                export_path = Path(param_value)
            else:
                export_path = paths.export_dir / param_value
            output_dirs.add(export_path.parent)
            rule.outputs.append(export_path)
            rule.parameters[param_name] = str(export_path)
            if "{doc}" in rule.parameters[param_name]:
                rule.doc_annotations.append(param_name)
            if "{" in param_value:
                rule.wildcard_annotations.append(param_name)
        # ExportInput
        elif isinstance(param.default, ExportInput):
            param_value, missing_configs = registry.expand_variables(param.default, rule.full_name)
            rule.missing_config.update(missing_configs)
            if param.default.absolute_path:
                rule.parameters[param_name] = param_value
            else:
                rule.parameters[param_name] = str(paths.export_dir / param_value)
            if param.default.all_docs:
                rule.inputs.extend(expand(escape_wildcards(rule.parameters[param_name]),
                                          doc=get_source_files(storage.source_files)))
            else:
                rule.inputs.append(rule.parameters[param_name])
            if "{" in rule.parameters[param_name]:
                rule.wildcard_annotations.append(param_name)
        # Config
        elif isinstance(param.default, Config):
            rule.parameters[param_name] = sparv_config.get(param.default, param.default.default)
        # Everything else with a default value
        elif param.default is not None:
            rule.parameters[param_name] = param.default

    storage.all_rules.append(rule)

    # Add to rule lists in storage
    update_storage(storage, rule)

    # Add exporter message
    if rule.exporter:
        rule.exit_message = "EXIT_MESSAGE: The exported files can be found in the following location{}:\n{}".format(
            "s" if len(output_dirs) > 1 else "", "\n".join(str(p / "_")[:-1] for p in output_dirs))

    if rule.missing_config:
        log_file = paths.log_dir / "{}.load_error.{}.log".format(os.getpid(), rule.full_name.replace(":", "."))
        log_file.parent.mkdir(parents=True, exist_ok=True)
        log_file.write_text("The following config variable{} need{} to be set:\n- {}".format(
            *("s", "") if len(rule.missing_config) > 1 else ("", "s"),
            "\n- ".join(rule.missing_config)))

    if config.get("debug"):
        print("    " + util.Color.BOLD + "INPUTS" + util.Color.RESET)
        for i in rule.inputs:
            print("        {}".format(i))
        print()
        print("    " + util.Color.BOLD + "OUTPUTS" + util.Color.RESET)
        for o in rule.outputs:
            print("        {}".format(o))
        print()
        print("    " + util.Color.BOLD + "PARAMETERS" + util.Color.RESET)
        for p in rule.parameters:
            print("        {} = {!r}".format(p, rule.parameters[p]))
        print()
        print()

    return True


def missing_defaults(params, rule):
    """Check if all parameters that need default values actually have default values."""
    for param_name, param in params.items():
        try:
            if param.default in [Annotation, Binary, Config, ExportAnnotations, ExportInput, Model, Output,
                                 ModelOutput, Export]:
                registry.expand_variables(param.default, rule.full_name)
        except Exception:
            return param_name
    return None


def populate_custom_rule(rule, params, storage, custom_rule_obj):
    """Populate rule with default values from custom_rule_obj."""
    # If rule name already exists, create a new name
    existing_rules = [r.rule_name for r in storage.all_rules]
    if rule.rule_name in existing_rules:
        rule.rule_name = create_new_rulename(rule.rule_name, existing_rules)
        rule.target_name = create_new_rulename(rule.target_name, [r.target_name for r in storage.all_rules])

    # Populate rule with custom values from config
    for out_param in custom_rule_obj.get("output", []):
        expand_custom_param(params, out_param, custom_rule_obj, rule.full_name)
    for param in custom_rule_obj.get("params", []):
        expand_custom_param(params, param, custom_rule_obj, rule.full_name)

    # Check if all parameters have received their values
    missing_default_param = missing_defaults(params, rule)
    if missing_default_param:
        error = f"Parameter '{missing_default_param}' in custom rule '{rule.full_name}' has no value!"
        log_handler.exit_with_message(error, os.getpid(), None, "sparv", "config")


def check_ruleorder(storage: SnakeStorage) -> Set[Tuple[RuleStorage, RuleStorage]]:
    """Order rules where necessary and print warning if rule order is missing."""
    ruleorder_pairs = set()
    ordered_rules = set()
    # Find rules that have common outputs and therefore need to be ordered
    for rule, other_rule in combinations(storage.all_rules, 2):
        common_outputs = tuple(sorted(set(rule.outputs).intersection(set(other_rule.outputs))))
        if common_outputs:
            # Check if a rule is lacking ruleorder or if two rules have the same order attribute
            if any(i is None for i in [rule.order, other_rule.order]) or rule.order == other_rule.order:
                ruleorder_pairs.add(((rule, other_rule), common_outputs))
            # Sort ordered rules
            else:
                ordered_rules.add(tuple(sorted([rule, other_rule], key=lambda i: i.order)))

    # Print warning if rule order is lacking somewhere
    for rules, common_outputs in ruleorder_pairs:
        rule1 = rules[0].full_name
        rule2 = rules[1].full_name
        common_outputs = ", ".join(map(str, common_outputs))
        print(util.sparv_warning(f"The annotators {rule1} and {rule2} have common outputs ({common_outputs}). "
              "Please make sure to set their 'order' arguments to different values."))

    return ordered_rules


def get_parameters(rule_params):
    """Extend function parameters with doc names and replace wildcards."""
    def get_params(wildcards):
        doc = get_doc_value(wildcards, rule_params.annotator)
        # We need to make a copy of the parameters, since the rule might be used for multiple documents
        _parameters = copy.deepcopy(rule_params.parameters)
        _parameters.update({name: doc for name in rule_params.docs})

        # Replace {doc} wildcard in parameters
        for name in rule_params.doc_annotations:
            _parameters[name] = _parameters[name].replace("{doc}", doc)

        # Replace wildcards (other than {doc}) in parameters
        for name in rule_params.wildcard_annotations:
            wcs = re.finditer(r"(?!{doc}){([^}]+)}", _parameters[name])
            for wc in wcs:
                _parameters[name] = _parameters[name].replace(wc.group(), wildcards.get(wc.group(1)))
        return _parameters
    return get_params


def update_storage(storage, rule):
    """Update info to snake storage with different targets."""
    if rule.exporter:
        storage.export_targets.append((rule.target_name, rule.description,
                                       rule.annotator_info["language"]))
    elif rule.installer:
        storage.install_targets.append((rule.target_name, rule.description))
    elif rule.modelbuilder:
        storage.model_targets.append((rule.target_name, rule.description, rule.annotator_info["language"]))
    else:
        storage.named_targets.append((rule.target_name, rule.description))

    if rule.annotator_info.get("order") is not None:
        storage.ordered_rules.append((rule.rule_name, rule.annotator_info))


def get_source_path() -> str:
    """Get path to source files."""
    return sparv_config.get("source_dir", paths.source_dir)


def get_annotation_path(annotation, data=False, common=False):
    """Construct a path to an annotation file given a doc and annotation."""
    elem, attr = util.split_annotation(annotation)
    path = Path(elem)

    if not (data or common):
        if not attr:
            attr = util.SPAN_ANNOTATION
        path = path / attr

    if not common:
        path = "{doc}" / path
    return path


def get_source_files(source_files) -> List[str]:
    """Get list of all available source files."""
    if not source_files:
        source_files = [f[1][0] for f in snakemake.utils.listfiles(
            Path(get_source_path(), "{file}." + sparv_config.get("source_type", "xml")))]
    return source_files


def prettify_config(in_config):
    """Prettify a yaml config string."""
    import yaml

    class MyDumper(yaml.Dumper):
        """Customized YAML dumper that indents lists."""

        def increase_indent(self, flow=False, indentless=False):
            """Force indentation."""
            return super(MyDumper, self).increase_indent(flow, False)

    # Resolve aliases and replace them with their anchors' contents
    yaml.Dumper.ignore_aliases = lambda *args: True
    yaml_str = yaml.dump(in_config, default_flow_style=False, Dumper=MyDumper, indent=4)
    # Colorize keys for easier reading
    yaml_str = re.sub(r"^(\s*[\S]+):", util.Color.BLUE + r"\1" + util.Color.RESET + ":", yaml_str,
                      flags=re.MULTILINE)
    return yaml_str


def escape_wildcards(s):
    """Escape all wildcards other than {doc}."""
    return re.sub(r"(?!{doc})({[^}]+})", r"{\1}", str(s))


def get_doc_value(wildcards, annotator):
    """Extract the {doc} part from full annotation path."""
    doc = None
    if hasattr(wildcards, "doc"):
        if annotator:
            doc = wildcards.doc[len(str(paths.annotation_dir)) + 1:]
        else:
            doc = wildcards.doc
    return doc


def load_config(snakemake_config):
    """Load corpus config and override the corpus language (if needed)."""
    # Find corpus config
    corpus_config_file = Path.cwd() / paths.config_file
    if corpus_config_file.is_file():
        config_missing = False
        # Read config
        sparv_config.load_config(corpus_config_file)

        # Add classes from config to registry
        registry.annotation_classes["config_classes"] = sparv_config.config.get("classes", {})
    else:
        config_missing = True

    # Some commands may override the corpus language
    if snakemake_config.get("language"):
        sparv_config.config["metadata"]["language"] = snakemake_config["language"]

    return config_missing


def get_install_targets(install_outputs):
    """Collect files to be created for all installations listed in config.install."""
    install_inputs = []
    for installation in sparv_config.get("korp.install", []):
        install_inputs.extend(install_outputs[installation])
    return install_inputs


def expand_custom_param(params, param_name, rule_info, rulename):
    """Expand a custom rule parameter with default values."""
    if not params.get(param_name):
        print(util.sparv_warning(f"The parameter '{param_name}'' used in one of your custom rules "
              f"does not exist in {rulename}"))
    else:
        param = params[param_name]
        # Expand output params
        if param.default in [Output, ModelOutput, Export]:
            out = rule_info["output"].get(param_name)
            params[param_name] = param.replace(default=param.default(out))
        # Expand other sparv params
        elif param.default in [Annotation, Binary, Config, ExportAnnotations, ExportInput, Model]:
            value = rule_info["params"].get(param_name)
            params[param_name] = param.replace(default=param.default(value))
        # Expand remaining params
        elif rule_info["params"].get(param_name) is not None:
            value = rule_info["params"].get(param_name)
            params[param_name] = param.replace(default=value)


def create_new_rulename(name, existing_names):
    """Create a new rule name by appending a number to it."""
    i = 2
    new_name = name + str(i)
    while new_name in existing_names:
        i += 1
        new_name = name + str(i)
    return new_name
