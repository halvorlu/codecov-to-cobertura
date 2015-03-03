# codecov-to-cobertura

`Codecov_to_cobertura.py` is a python script to convert from XML produced by Intel's `codecov` tool to Cobertura XML format.
This format can be read by e.g. [Hudson/Jenkins](https://github.com/jenkinsci/jenkins) to generate coverage reports.
See e.g. [intel.com](https://software.intel.com/sites/default/files/article/401105/code-coverage.pdf) for more info on `codecov`.

## Usage

* After compiling your C++/Fortran code with the `-prof-gen=srcpos` flag and running it, two files `pgopti.dpi` and `pgopti.spi` should have been produced.
* The `codecov` tool can now be used: `codecov -prj <projectname> -dpi pgopti.dpi -spi pgopti.spi -xmlbcvrg codecov.xml`, which should produce an XML file `codecov.xml`
* Finally the `codecov_to_cobertura.py` script can be used to generate a Cobertura XML file: `python codecov_to_cobertura.py codecov.xml <src_path> <object_path> coverage.xml` where `<src_path>` and `<object_path>` are the paths to your source and object files, respectively.

For more description of the command-line arguments to `codecov_to_cobertura.py`, try `codecov_to_cobertura.py -h`.