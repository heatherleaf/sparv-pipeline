"""Printing functions for Snakefile."""

from sparv import util
from sparv.core import registry, snake_utils


def prettify_config(in_config):
    """Prettify a yaml config string."""
    import re

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


def print_module_info(module_types, module_names, snake_storage, reverse_config_usage):
    """Wrap module printing functions: print correct info for chosen module_types and module_names."""
    all_module_types = {
        "annotators": print_annotators,
        "importers": print_importers,
        "exporters": print_exporters,
        "custom_annotators": print_custom_annotators
    }

    if not module_types:
        module_types = all_module_types.keys()

    module_names = [n.lower() for n in module_names]

    # Print module info for all chosen module_types
    if not module_names:
        for m in module_types:
            print_func = all_module_types.get(m)
            print_func(snake_storage, reverse_config_usage)

    # Print only info for chosen module_names
    else:
        # TODO: check if module name is valid!
        for m in module_types:
            print_func = all_module_types.get(m)
            print_func(snake_storage, reverse_config_usage, only_modules=module_names)


def print_annotators(snake_storage, reverse_config_usage, print_params=False, only_modules=[]):
    """Print info about annotators."""
    modules = snake_storage.all_annotations
    if only_modules:
        modules = dict((k, v) for k, v in snake_storage.all_annotations.items() if k in only_modules)
    if modules:
        max_len = max(len(a[0]) for m in modules for f in modules[m] for a in modules[m][f]["annotations"]) + 4
        print_modules(modules, "annotators", reverse_config_usage, snake_storage, max_len,
                      print_params=print_params)


def print_importers(snake_storage, reverse_config_usage, print_params=False, only_modules=[]):
    """Print info about importers."""
    modules = snake_storage.all_importers
    if only_modules:
        modules = dict((k, v) for k, v in snake_storage.all_importers.items() if k in only_modules)
    if modules:
        configs = [reverse_config_usage.get(f"{module_name}:{f_name}") for module_name in modules for f_name in
                   modules[module_name] if reverse_config_usage.get(f"{module_name}:{f_name}")]
        max_len = max(len(k[0]) for li in configs for k in li) + 4
        print_modules(modules, "importers", reverse_config_usage, snake_storage, max_len, print_params=print_params)


def print_exporters(snake_storage, reverse_config_usage, print_params=False, only_modules=[]):
    """Print info about exporters."""
    modules = snake_storage.all_exporters
    if only_modules:
        modules = dict((k, v) for k, v in snake_storage.all_exporters.items() if k in only_modules)
    if modules:
        configs = [reverse_config_usage.get(f"{module_name}:{f_name}") for module_name in modules for f_name in
                   modules[module_name] if reverse_config_usage.get(f"{module_name}:{f_name}")]
        max_len = max(len(k[0]) for li in configs for k in li) + 4
        print_modules(modules, "exporters", reverse_config_usage, snake_storage, max_len, print_params=print_params)


def print_custom_annotators(snake_storage, reverse_config_usage, print_params=True, only_modules=[]):
    """Print info about custom annotations."""
    modules = snake_storage.all_custom_annotations
    if only_modules:
        modules = dict((k, v) for k, v in snake_storage.all_custom_annotations.items() if k in only_modules)
    if modules:
        max_len = max(len(a) for m in modules for f in modules[m] for a in modules[m][f]["params"]) + 4
        print_modules(modules, "custom annotation functions", reverse_config_usage, snake_storage, max_len,
                      print_params=print_params)


def print_annotation_classes():
    """Print info about annotation classes."""
    max_len = max(len(cls) for cls in registry.annotation_classes["module_classes"]) + 8
    print()
    print("Available annotation classes")
    print("============================\n")
    print(util.Color.BOLD + "    Classes defined by pipeline modules" + util.Color.RESET)
    print("        {}{:{}}    {}{}".format(util.Color.ITALIC, "Class", max_len, "Annotation", util.Color.RESET))
    for cls, anns in registry.annotation_classes["module_classes"].items():
        print("        {:{}}    {}".format(cls, max_len, anns[0]))
        if len(anns) > 1:
            for ann in anns[1:]:
                print("        {:{}}    {}".format("", max_len, ann))
    if registry.annotation_classes["config_classes"]:
        print()
        print(util.Color.BOLD + "    Classes from config" + util.Color.RESET)
        print("        {}{:{}}    {}{}".format(util.Color.ITALIC, "Class", max_len, "Annotation", util.Color.RESET))
        for cls, ann in registry.annotation_classes["config_classes"].items():
            print("        {:{}}    {}".format(cls, max_len, ann))
    print()


def print_modules(modules: dict, module_name: str, reverse_config_usage: dict, snake_storage: snake_utils.SnakeStorage,
                  max_len: int, print_annotations: bool = True, print_params: bool = False):
    """Print module information."""
    custom_annotations = snake_storage.all_custom_annotations

    print()
    print(f"Available {module_name}")
    print("==========" + "=" * len(module_name) + "\n")
    for module_name in sorted(modules):
        print(util.Color.BOLD + "{}".format(module_name.upper()) + util.Color.RESET)
        for f_name in sorted(modules[module_name]):
            print("      {}{}{}".format(util.Color.UNDERLINE, f_name, util.Color.RESET))
            f_desc = modules[module_name][f_name]["description"]
            if f_desc:
                print("      {}".format(f_desc))
            print()

            f_anns = modules[module_name][f_name].get("annotations", {})
            if print_annotations and f_anns:
                print("      Annotations:")
                for f_ann in sorted(f_anns):
                    print("        • {:{width}}{}".format(f_ann[0], f_ann[1] or "", width=max_len))
                    if f_ann[0].cls:
                        print(util.Color.ITALIC + "          <{}>".format(f_ann[0].cls) + util.Color.RESET)
                print()

            f_config = reverse_config_usage.get(f"{module_name}:{f_name}")
            if f_config:
                print("      Configuration variables used:")
                for config_key in sorted(f_config):
                    print("        • {:{width}}{}".format(config_key[0], config_key[1] or "", width=max_len))
                print()

            # Always print parameters for custom annotations
            params = modules[module_name][f_name].get("params", {})
            custom_params = None
            if custom_annotations.get(module_name, {}).get(f_name, {}):
                custom_params = custom_annotations[module_name][f_name].get("params", {})
                params = custom_params

            if (print_params and params) or custom_params:
                print("      Arguments:")
                for p, (default, typ, li, optional) in params.items():
                    opt_str = "(optional) " if optional else ""
                    typ_str = "list of " + typ.__name__ if li else typ.__name__
                    def_str = f", default: {repr(default)}" if default is not None else ""
                    print("        • {:{width}}{}{}{}".format(p, opt_str, typ_str, def_str, width=max_len))
                print()