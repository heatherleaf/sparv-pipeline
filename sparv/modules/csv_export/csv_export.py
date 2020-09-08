"""CSV file export."""

import logging
import os
from typing import Optional

import sparv.util as util
from sparv import Annotation, Config, Document, Export, ExportAnnotations, exporter

log = logging.getLogger(__name__)


@exporter("CSV export", config=[Config("csv_export.delimiter", default="\t")])
def csv(doc: Document = Document(),
        out: Export = Export("csv/{doc}.csv"),
        token: Annotation = Annotation("<token>"),
        word: Annotation = Annotation("<token:word>"),
        sentence: Annotation = Annotation("<sentence>"),
        annotations: ExportAnnotations = ExportAnnotations("csv_export.annotations"),
        source_annotations: Optional[list] = Config("csv_export.source_annotations"),
        remove_namespaces: bool = Config("export.remove_export_namespaces", False),
        delimiter: str = Config("csv_export.delimiter")):
    """Export annotations to CSV format."""
    # Create export dir
    os.makedirs(os.path.dirname(out), exist_ok=True)

    token_name = token.name

    # Read words
    word_annotation = list(word.read())

    # Get annotation spans, annotations list etc.
    annotation_list, token_attributes, export_names = util.get_annotation_names(annotations, source_annotations,
                                                                                doc=doc, token_name=token_name,
                                                                                remove_namespaces=remove_namespaces)
    span_positions, annotation_dict = util.gather_annotations(annotation_list, export_names, doc=doc)

    # Make csv header
    csv_data = [make_header(token_name, token_attributes, export_names, delimiter)]

    # Go through spans_dict and add to csv, line by line
    for _pos, instruction, span in span_positions:
        if instruction == "open":
            # Create token line
            if span.name == token_name:
                csv_data.append(make_token_line(word_annotation[span.index], token_name, token_attributes,
                                                annotation_dict, span.index, delimiter))

            # Create line with structural annotation
            else:
                attrs = make_attrs(span.name, annotation_dict, export_names, span.index)
                for attr in attrs:
                    csv_data.append(f"# {attr}")
                if not attrs:
                    csv_data.append(f"# {span.export}")

        # Insert blank line after each closing sentence
        elif span.name == sentence and instruction == "close":
            csv_data.append("")

    # Write result to file
    with open(out, "w") as f:
        f.write("\n".join(csv_data))
    log.info("Exported: %s", out)


def make_header(token, token_attributes, export_names, delimiter):
    """Create a csv header containing the names of the token annotations."""
    line = [export_names.get(token, token)]
    for annot in token_attributes:
        line.append(export_names.get(":".join([token, annot]), annot))
    return delimiter.join(line)


def make_token_line(word, token, token_attributes, annotation_dict, index, delimiter):
    """Create a line with the token and its annotations."""
    line = [word.replace(delimiter, " ")]
    for attr in token_attributes:
        if attr not in annotation_dict[token]:
            attr_str = util.UNDEF
        else:
            attr_str = annotation_dict[token][attr][index]
        line.append(attr_str)
    return delimiter.join(line)


def make_attrs(annotation, annotation_dict, export_names, index):
    """Create a list with attribute-value strings for a structural element."""
    attrs = []
    for name, annot in annotation_dict[annotation].items():
        export_name = export_names.get(":".join([annotation, name]), name)
        annotation_name = export_names.get(annotation, annotation)
        attrs.append("%s.%s = %s" % (annotation_name, export_name, annot[index]))
    return attrs
