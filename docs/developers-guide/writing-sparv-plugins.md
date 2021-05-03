# Writing Sparv Plugins
The Sparv Pipeline is comprised of different modules like importers, annotators and exporters. Although many modules are
shipped with the main Sparv package none of these modules are hard-coded into the Sparv Pipeline and therefore it can
easily be extended with plugins. A plugin is a Sparv module that is not part of the main Sparv package. Writing a plugin
is the recommended way of adding a new module to Sparv.

When writing your first plugin we recommend that you take a look at the [Sparv plugin
template](https://github.com/spraakbanken/sparv-plugin-template). The template contains an example of a small annotation
module that converts tokens to uppercase. We will use this template in the examples below.


## Plugin Structure
This is what a typical structure of a plugin may look like:
```
sparv-uppercase/
├── uppercase
│   ├── uppercase.py
│   └── __init__.py
├── LICENSE
├── README.md
└── setup.py
```

In the above example the `uppercase` directory is a Sparv module containing the [module code](#module-code) in
`uppercase.py` and the mandatory [init file](#init-file) `__init__.py`. The [setup file](#setup-file) `setup.py` in the
root directory is needed in order to install the plugin. A plugin does not have to be stored in any particular place. As
long as the Sparv Pipeline is installed on your machine, you should be able to inject your plugin into the Sparv
Pipeline code using pipx (from the directory containing your plugin):
```bash
pipx inject sparv-pipeline ./sparv-uppercase
```

After the injection the plugin functionality should be available, and the plugged-in module should be treated just like
any other module within the Sparv Pipeline.

The readme and license files are not strictly recommended are not strictly necessary for the plugin to work but we
strongly recommend that you include these if you want to publish your plugin.


## Setup File
The `setup.py` is needed in order to install a plugin and connect it to the Sparv Pipeline. Here is a minimal example of
a setup file (taken from the [Sparv plugin template](https://github.com/spraakbanken/sparv-plugin-template)):
```python
import setuptools

setuptools.setup(
    name="uppercase",
    version="0.1",
    description="Uppercase converter (example plug-in for Sparv)",
    license="MIT",
    packages=["uppercase"],
    python_requires=">=3.6",
    install_requires=["sparv-pipeline>=4"],
    entry_points={"sparv.plugin": ["uppercase = uppercase"]}
)
```

Make sure to include the name of your module (i.e. the directory containing the Sparv code) in `packages`. You also need
to make sure that there is a `sparv.plugin` entry point in `entry_points` that points to your module.

For more information about Python setup scripts check the [distutils
documentation](https://docs.python.org/3/distutils/setupscript.html).


## Init File
Each Sparv module must contain a [Python init file](https://docs.python.org/3/reference/import.html#regular-packages)
(`__init__.py`). Without the init file Sparv will not be able to register the module. The Python scripts containing
decorated Sparv functions should be imported here. Module-specific configuration parameters may also be declared in this
file. Furthermore, you should provide a short description (one sentence) for your module which will be displayed to the
user when running the `sparv modules` command. The description is provided either as an argument to `__description__` or
as a docstring. In the example below we use both, but only one of them is necessary. If both exist, the value of
`__description__` is displayed in the `sparv modules` command.

Example of an `__init__.py` file:
```python
"""Example for a Sparv annotator that converts tokens to uppercase."""

# from sparv import Config

from . import uppercase

# __config__ = [
#     Config("uppercase.some_setting", "some_default_value", description="Description for this setting")
# ]

__description__ = "Example for a Sparv annotator that converts tokens to uppercase."
```


## Module Code
A Sparv module is a Python package containing at least one Python script that imports [Sparv
classes](developers-guide/sparv-classes) (and [util functions](developers-guide/utilities) if needed) which are used for
describing dependencies to other entities (e.g. annotations or models) handled or created by the pipeline. Here is the
code for or uppercase example (taken from the [Sparv plugin
template](https://github.com/spraakbanken/sparv-plugin-template):
```python
from sparv import Annotation, Output, annotator

@annotator("Convert every word to uppercase.")
def uppercase(word: Annotation = Annotation("<token:word>"),
              out: Output = Output("<token>:uppercase.upper")):
    """Convert to uppercase."""
    out.write([val.upper() for val in word.read()])
```

In this script we import two classes from Sparv (`Annotation` and `Output`) and the `annotator` decorator. Please note
that nothing should be imported from the Sparv code unless it is directly available from the sparv package (i.e. `from
sparv import ...`), or the `sparv.util` sub-package. Any other sub-packages (like `sparv.core`) are for internal use
only, and are subject to change without notice.

Our `uppercase` function is decorated with `@annotator` which tells Sparv that this function can be used to produce one
or more annotations. The first argument in the decorator is its description which is used for displaying help texts in
the CLI (e.g. when running `sparv modules`).

The function's relation to other pipeline components is described by its signature. The function arguments contain type
hints to the Sparv classes `Annotation` and `Output` which indicate what dependencies (e.g. annotations, models or
config variables) must be satisfied before the function can do its job, and what it will produce. In this example Sparv
will make sure that a word annotation exists before it will attempt to call the `uppercase` function, because it knows
that `word` is an input since it is of type `Annotation`. It also knows that the function produces the output annotation
`<token>:uppercase.upper`, so if any other module would request this annotation as input, it will run `uppercase`
prior to calling that module.

A function decorated with a Sparv decorator should never be actively called by you or by another decorated function.
When running Sparv through the CLI Sparv's dependency system will calculate a dependency graph and all the functions
necessary for producing the desired output will be run automatically.


## Reading and Writing Files
Sparv classes like `Annotation` and `Output` have built-in methods for reading and writing files (like `word.read()` and
`out.write()` in the above example). A Sparv module should never read or write any files without using the provided
class methods. This is to make sure that files are written to the correct places in the file structure so that they can
be found by other modules. The read and write methods also make sure that Sparv's internal data format is handled
correctly. Not using these provided methods can lead to procedures breaking if the internal data format or file
structure is updated in the future.


## Logging
Logging from Sparv modules is done with [Python's logging library](https://docs.python.org/3.6/library/logging.html).
Please use the provided `get_logger` wrapper when declaring your logger which takes care of importing the logging
library and sets the correct module name in the log output:
```python
import sparv.util as util
logger = util.get_logger(__name__)
logger.error("An error was encountered!")
```

Any of the official [Python logging levels](https://docs.python.org/3.6/library/logging.html#levels) may be used.

By default, Sparv will write log output with level WARNING and higher to the terminal. The user can change the log level
with the flag `--log [LOGLEVEL]`. Most commands support this flag. The user can also choose to write the log output to a
file by using the `--log-to-file [LOGLEVEL]` flag. The log file will receive the current date and timestamp as filename
and can be found inside `logs/` in the corpus directory.


## Error Messages
When raising critical errors that should be displayed to the user (e.g. to tell the user that he/she did something
wrong) you should use the [SparvErrorMessage class](developers-guide/utilities#SparvErrorMessage). This will raise an
exception (and thus stop the current Sparv process) and notify the user of errors in a friendly way without displaying
the usual Python traceback.
```python
@annotator("Convert every word to uppercase")
def uppercase(word: Annotation = Annotation("<token:word>"),
              out: Output = Output("<token>:uppercase.upper"),
              important_config_variable: str = Config("uppercase.some_setting")):
    """Convert to uppercase."""
    # Make sure important_config_variable is set by the user
    if not important_config_variable:
        raise util.SparvErrorMessage("Please make sure to set the config variable 'uppercase.some_setting'!")
    ...
```


## Advanced Features
This section contains documentation for more advanced features which may be used but are not necessary for writing
plugins.

### Function Order
Sometimes one may want to create multiple Sparv functions that create the same output files (e.g. annotation files,
export files or model files). In this case Sparv needs to be informed about the priority of these functions. Let's say
that there are two functions `annotate()` and `annotate_backoff()` that both produce an annotation output called
`mymodule.foo`. Ideally `mymodule.foo` should be produced by `annotate()` but if this function cannot be run for some
reason (e.g. because it needs another annotation file `mymodule.bar` that cannot be produced for some corpora), then you
want `mymodule.foo` to be produced by `annotate_backoff()`. The priority of functions is stated with the `order`
argument in the `@annotator`, `@exporter`, or `@modelbuilder` decorator. The integer value given by `order` will help
Sparv decide which function to try to use first. A lower number indicates higher priority.
```python
@annotator("Create foo annotation", order=1)
def annotate(
    out: Output = Output("mymodule.foo"),
    bar_input: Annotation = Annotation("mymodule.bar")):
    ...


@annotator("Create foo annotation for when bar is not available", order=2)
def annotate_backoff(
    out: Output = Output("mymodule.foo")):
    ...
```

<!-- Functions with a higher order number can explicitly be called with `sparv run-rule`. Not working at the moment due
to a bug! -->


### Preloaders
Preloader functions are used by the `sparv preload` command to speed up the annotation process. It works by
preloading the Python module together with models or processes which would otherwise need to be loaded once for every
source file.

A preload function is simply a function that takes a subset of the arguments from an annotator, and returns a value that
is passed on to the annotator. Here is an example:

```python
from sparv import Annotation, Model, Output, annotator


def preloader(model):
    """Preload POS-model."""
    return load_model(model)


@annotator("Part-of-speech tagging.",
           preloader=preloader,
           preloader_params=["model"],
           preloader_target="model_preloaded")
def pos_tag(word: Annotation = Annotation("<token:word>"),
            out: Output = Output("<token>:pos.tag"),
            model: Model = Model("pos.model"),
            model_preloaded=None):
    """Annotate tokens with POS tags."""
    if model_preloaded:
        model = model_preloaded
    else:
        model = load_model(model)
```

This annotator uses a model. It also has an extra argument called `model_preloaded` which can optionally take
an already loaded model. In the decorator we point out the preloader function using the `preloader` parameter.
`preloader_params` is a list of parameter names from the annotator, which the preloader needs as arguments. In this
case it's only one: the `model` parameter. `preloader_target` points to a single parameter name of the annotator, which
is the one that will recieve the return value from the preloader function.

When using the `sparv preload` command with this annotator, the preloader function will be run only once, and every
time the annotator is used, it will get the preloaded model via the `model_preloaded` parameter.

The three decorator parameters `preloader`, `preloader_params` and `preloader_target` are all required when adding
a preloader to an annotator. Additionally, there are two optional parameters that can be used: `preloader_shared`
and `preloader_cleanup`.

`preloader_shared` is a boolean with a default value of True. By default, Sparv will run the preloader function
only once, and if using `sparv preload` with multiple parallel processes, they will all share the result from the
preloader. By setting `preloader_shared` to False, the preloader function will instead be run once per process.
This is usually only needed when preloading processes, rather than models.

`preloader_cleanup` refers to a function, just like the `preloader` parameter. This function will be run after every
(preloaded) use of the annotator. As arguments the cleanup function should take the same arguments as the preloader
function, plus an extra argument for receiving the return value of the preloader function. It should return the same
kind of object as the preloader function, which will then be used by Sparv as the new preloaded value. This is rarely
needed, but one possible use case is when preloading a process that for some reason needs to be regularly restarted. The
cleanup function would then keep track of when restarting is needed, call the preloader function to start a new process,
and then return it.