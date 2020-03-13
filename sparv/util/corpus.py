import os
import heapq
from . import log

######################################################################
# Annotations

DOC_CHUNK_DELIM = ":"
ELEM_ATTR_DELIM = ":"
SPAN_ANNOTATION = "@span"
TEXT_FILE = "@text"
DEFAULT_CORPUS_DIR = ""


def annotation_exists(doc, annotation):
    """Check if an annotation file exists."""
    annotation_path = get_annotation_path(doc, annotation)
    return os.path.exists(annotation_path)


def clear_annotation(doc, annotation):
    """Remove an annotation file if it exists."""
    elem, attr = split_annotation(annotation)
    annotation_path = get_annotation_path(doc, annotation)
    if os.path.exists(annotation_path):
        os.remove(annotation_path)


def write_annotation(doc, annotation, values, append=False):
    """Write an annotation to one or more files. The file is overwritten if it exists.
    The annotation should be a list of values."""
    if isinstance(annotation, str):
        annotation = annotation.split()

    if len(annotation) == 1:
        # Handle single annotation
        _write_single_annotation(doc, annotation[0], values, append)
    else:
        elem_attrs = dict(split_annotation(ann) for ann in annotation)
        # Handle multiple annotations used as one
        assert all(elem_attrs.values()), "Span annotations can not be written while treating multiple annotations as one."
        # Get spans and associated names for annotations
        spans = read_annotation(doc, elem_attrs.keys(), with_annotation_name=True)
        annotation_values = {elem: [] for elem in elem_attrs.keys()}

        for value in values:
            _, annotation_name = next(spans)
            annotation_values[annotation_name].append(value)

        for annotation_name in annotation_values:
            _write_single_annotation(doc, join_annotation(annotation_name, elem_attrs[annotation_name]),
                                     annotation_values[annotation_name], append)


def _write_single_annotation(doc, annotation, values, append):
    """Write an annotation to a file."""
    is_span = not split_annotation(annotation)[1]
    file_path = get_annotation_path(doc, annotation)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    mode = "a" if append else "w"
    with open(file_path, mode) as f:
        ctr = 0
        for value in values:
            if value is None:
                value = ""
            elif is_span:
                start, end = value
                start_subpos, end_subpos = None, None
                if isinstance(start, tuple):
                    start, start_subpos = start
                if isinstance(end, tuple):
                    end, end_subpos = end
                start_subpos = ".{}".format(start_subpos) if start_subpos else ""
                end_subpos = ".{}".format(end_subpos) if end_subpos else ""
                value = "{}{}-{}{}".format(start, start_subpos, end, end_subpos)
            else:
                # value = value.replace("\\", r"\\").replace("\n", r"\n").replace("\r", "")  # Use if we allow linebreaks in tokens
                value = value.replace("\n", "").replace("\r", "")  # Don't allow linebreaks in tokens
            print(value, file=f)
            ctr += 1
    # Update file modification time even if nothing was written
    os.utime(file_path, None)
    log.info("Wrote %d items: %s/%s", ctr, doc, annotation)


def create_empty_attribute(doc, annotation):
    """Return a list filled with None of the same size as 'annotation'."""
    return [None] * len(list(read_annotation_spans(doc, annotation)))


def read_annotation_spans(doc, annotation, decimals=False, with_annotation_name=False):
    """Iterate over the spans of an annotation."""
    # Strip any annotation attributes
    annotation = [split_annotation(ann)[0] for ann in annotation.split()]
    for span in read_annotation(doc, annotation, with_annotation_name):
        if not decimals:
            yield tuple(v[0] for v in span)
        else:
            yield span


def read_annotation(doc, annotation, with_annotation_name=False):
    """An iterator that yields each line from an annotation file."""
    if isinstance(annotation, str):
        annotation = annotation.split()
    if len(annotation) == 1:
        # Handle single annotation
        yield from _read_single_annotation(doc, annotation[0], with_annotation_name)
    else:
        # Handle multiple annotations used as one
        yield from heapq.merge(*[_read_single_annotation(doc, ann, with_annotation_name)
                                 for ann in annotation])


def read_annotation_attributes(doc, annotations, with_annotation_name=False):
    """Iterator that yields tuples of multiple annotations."""
    assert isinstance(annotations, (tuple, list)), "'annotations' argument must be tuple or list"
    assert len(set(split_annotation(annotation)[0] for annotation in annotations)), "All attributes need to be for " \
                                                                                    "the same annotation spans"
    return zip(*[read_annotation(doc, annotation, with_annotation_name)
                 for annotation in annotations])


def _read_single_annotation(doc, annotation, with_annotation_name):
    """Internal function for reading a single annotation file."""
    ann_file = get_annotation_path(doc, annotation)

    with open(ann_file, "r") as f:
        ctr = 0
        for line in f:
            value = line.rstrip("\n\r")
            if not split_annotation(annotation)[1]:  # If this is a span annotation
                value = tuple(tuple(map(int, pos.split("."))) for pos in value.split("-"))
            # value = re.sub(r"((?<!\\)(?:\\\\)*)\\n", "\1\n", value).replace(r"\\", "\\")  # Replace literal "\n" with linebreak (only needed if we allow "\n" in tokens)
            yield value if not with_annotation_name else (value, annotation)
            ctr += 1
    log.info("Read %d items: %s/%s", ctr, doc, annotation)


def split_annotation(annotation):
    elem, _, attr = annotation.partition(ELEM_ATTR_DELIM)
    return elem, attr


def join_annotation(name, attribute):
    return ELEM_ATTR_DELIM.join((name, attribute))


def get_annotation_path(doc, annotation):
    """Construct a path to an annotation file given a doc and annotation."""
    doc, _, chunk = doc.partition(DOC_CHUNK_DELIM)
    elem, attr = split_annotation(annotation)
    corpus_dir = os.environ.get("CORPUS_DIR", DEFAULT_CORPUS_DIR)
    annotation_dir = os.path.join(corpus_dir, "annotations")

    if elem == TEXT_FILE:
        return os.path.join(annotation_dir, doc, chunk, elem)
    elif not attr:
        attr = SPAN_ANNOTATION
    return os.path.join(annotation_dir, doc, chunk, elem, attr)


def chain(annotations, default=None):
    """Create a functional composition of a list of annotations.
    E.g., token.sentence + sentence.id -> token.sentence-id

    >>> from pprint import pprint
    >>> pprint(dict(
    ...   chain([{"w:1": "s:A",
    ...           "w:2": "s:A",
    ...           "w:3": "s:B",
    ...           "w:4": "s:C",
    ...           "w:5": "s:missing"},
    ...          {"s:A": "text:I",
    ...           "s:B": "text:II",
    ...           "s:C": "text:mystery"},
    ...          {"text:I": "The Bible",
    ...           "text:II": "The Samannaphala Sutta"}],
    ...         default="The Principia Discordia")))
    {'w:1': 'The Bible',
     'w:2': 'The Bible',
     'w:3': 'The Samannaphala Sutta',
     'w:4': 'The Principia Discordia',
     'w:5': 'The Principia Discordia'}
    """
    def follow(key):
        for annot in annotations:
            try:
                key = annot[key]
            except KeyError:
                return default
        return key
    return ((key, follow(key)) for key in annotations[0])


def lexicon_to_pickle(lexicon, filename, protocol=-1, verbose=True):
    """Save lexicon as a pickle file."""
    import pickle
    if verbose:
        log.info("Saving lexicon in pickle format")
    with open(filename, "wb") as F:
        pickle.dump(lexicon, F, protocol=protocol)
    if verbose:
        log.info("OK, saved")


def test_annotations(lexicon, testwords):
    """
    For testing the validity of a lexicon.
    Takes a dictionary (lexicon) and a list of test words.
    Prints the value for each test word.
    """
    log.info("Testing annotations...")
    for key in testwords:
        log.output("  %s = %s", key, lexicon.get(key))


class PickledLexicon(object):
    """Read basic pickled lexicon and look up keys."""
    def __init__(self, picklefile, verbose=True):
        import pickle
        if verbose:
            log.info("Reading lexicon: %s", picklefile)
        with open(picklefile, "rb") as F:
            self.lexicon = pickle.load(F)
        if verbose:
            log.info("OK, read %d words", len(self.lexicon))

    def lookup(self, key, default=set()):
        """Lookup a key in the lexicon."""
        return self.lexicon.get(key, default)


######################################################################
# Corpus text

def read_corpus_text(doc):
    """Read the text contents of a corpus and return as a string."""
    text_file = get_annotation_path(doc, TEXT_FILE)
    with open(text_file, "r") as f:
        text = f.read()
    log.info("Read %d chars: %s", len(text), text_file)
    return text


def write_corpus_text(doc, text):
    """Write text to the designated file of a corpus.
    text is a unicode string.
    """
    doc, _, chunk = doc.partition(DOC_CHUNK_DELIM)
    text_file = get_annotation_path(doc, TEXT_FILE)
    print(doc, text_file)
    os.makedirs(os.path.dirname(text_file), exist_ok=True)
    with open(text_file, "w") as f:
        f.write(text)
    log.info("Wrote %d chars: %s", len(text), text_file)
