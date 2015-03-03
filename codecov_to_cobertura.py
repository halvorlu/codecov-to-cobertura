#!/usr/bin/env python2
"""
A python script to produce Cobertura XML from Intel's codecov XML.
"""
from xml.etree.ElementTree import ElementTree, Element
import os.path
import re


def main(from_file, to_file, object_path, source_path, out_source_path):
    """Produce Cobertura XML from Intel's codecov XML.

    from_file: XML file produced by Intel's codecov
    to_file: XML file to be written
    object_path: Relative path to directory with object files
    source_path: Relative path to directory with source files"""
    root = root_from_file(from_file)
    project_name = root.get("name", "")
    classes = Element("classes")
    for module in root.findall("MODULE"):
        if not module_in_source(module, source_path):
            continue
        class_elem = module_to_class(module, source_path)
        classes.append(class_elem)
    add_missing_files(classes, source_path)
    for class_elem in classes.findall("class"):
        add_missing_methods(class_elem, object_path)
        create_lines(class_elem)
        replace_source_path(class_elem, out_source_path)
    total_branch_rate = str(calc_total_branch_rate(root.iter("BLOCKS")))
    package = Element("package", attrib={"branch-rate": total_branch_rate,
                                         "name": project_name})
    package.append(classes)
    packages = Element("packages")
    packages.append(package)
    new_root = Element("coverage", attrib={"branch-rate": total_branch_rate,
                                           "line-rate": total_branch_rate,
                                           "version": "3.7.1",
                                           "timestamp": str(unix_timestamp())})
    new_root.append(packages)
    new_tree = ElementTree(new_root)
    with open(to_file, 'w') as fileobj:
        fileobj.write("<?xml version=\"1.0\" ?><!DOCTYPE coverage SYSTEM 'http://cobertura.sourceforge.net/xml/coverage-03.dtd'>")
        new_tree.write(fileobj)


def replace_source_path(class_elem, new_path):
    """Replace the source path in the given class element."""
    oldfile = os.path.basename(class_elem.get("filename"))
    new_file_path = os.path.join(new_path, oldfile)
    class_elem.set("filename", new_file_path)


def add_missing_files(classes, source_path):
    """Add class element for files in source_path that are missing."""
    from os import listdir
    from os.path import isfile, join
    found_files = [x.get("filename") for x in classes.findall("class")]
    all_files = [f for f in listdir(source_path)
                 if isfile(join(source_path, f))]
    for filename in all_files:
        filepath = join(source_path, filename)
        if filepath not in found_files and is_fortran(filepath):
            classes.append(empty_class(filepath))


def empty_class(filepath):
    """Return an element representing an empty class."""
    class_elem = Element("class", attrib={"name": filepath,
                                          "branch-rate": "0",
                                          "line-rate": "0",
                                          "complexity": "0",
                                          "filename": filepath})
    class_elem.append(Element("methods"))
    return class_elem


def is_fortran(filepath):
    """Return True if given filename is a fortran file."""
    if re.search(r"\.(f|f90)$", filepath, flags=re.IGNORECASE):
        return True
    else:
        return False


def module_in_source(module, source_path):
    """Return True if given MODULE element contains the given path."""
    module_path = module.get("name", "unknown")
    return source_path in module_path


def create_lines(class_elem):
    """Create lines node to class node by copying lines from methods."""
    lines = Element("lines")
    for line in class_elem.iter("line"):
        lines.append(line)
    class_elem.append(lines)


def unix_timestamp():
    """Return the current UNIX timestamp."""
    from datetime import datetime
    import calendar
    dt_now = datetime.utcnow()
    return calendar.timegm(dt_now.utctimetuple())


def add_missing_methods(class_elem, object_path):
    """Add missing methods to given class node, using given object path."""
    filename = class_elem.get("filename")
    basename = os.path.basename(filename)
    object_file = basename.split(".")[0] + ".o"
    object_file_path = os.path.join(object_path, object_file)
    file_methods = methods_in_file(object_file_path)
    node_methods = class_elem.find("methods")
    found_methods = [method.get("name")
                     for method in node_methods.findall("method")]
    for method in file_methods:
        if method not in found_methods:
            try:
                node_methods.append(uncalled_method(method, filename))
            except Exception as e:
                print "Warning: " + str(e)


def uncalled_method(name, filename):
    """Return a method node representing an uncalled method called 'name'."""
    method = Element("method", attrib={"name": name,
                                       "branch-rate": "0",
                                       "line-rate": "0",
                                       "signature": ""})
    start_line, end_line = function_line_span(filename, name)
    lines = Element("lines")
    for lineno in executable_lines(filename, start_line, end_line):
        lines.append(Element("line",
                             attrib={"hits": "0", "number": str(lineno)}))
    method.append(lines)
    return method


def function_line_span(filename, function):
    """Return the start/end line number of the given function."""
    re_obj = re.compile(r"^[^!]*(subroutine|function) "+function,
                        flags=re.IGNORECASE)
    start_line = match_line_number(filename, re_obj)
    re_obj = re.compile(r"^[^!]*end (subroutine|function)",
                        flags=re.IGNORECASE)
    end_line = match_line_number(filename, re_obj, start_line+1)
    return start_line, end_line


def executable_lines(filename, start_line, end_line):
    """Return a list of line numbers that are executable."""
    executable = []
    prev_line = ''
    with open(filename, "r") as fileobj:
        lineno = 0
        for line in fileobj:
            lineno += 1
            if lineno < start_line:
                continue
            if lineno > end_line:
                break
            if is_executable_line(line, prev_line):
                executable.append(lineno)
            prev_line = line

    return executable


NON_COMMENT_PATTERN = re.compile(r"^\s*[a-z]+", flags=re.IGNORECASE)
USE_PATTERN = re.compile(r"^\s*use [a-z]+", flags=re.IGNORECASE)
CONT_PATTERN = re.compile(r".*&\s*$")
VAR_PATTERN = re.compile(r"[^!]*::")
END_PATTERN = re.compile(r"\s*(end\s*do|end\s*if|end\s*select)")
IMPLICIT_PATTERN = re.compile(r"\s*implicit ")
ELSE_PATTERN = re.compile(r"\s*else ")


def is_executable_line(line, prev_line=''):
    """Return True if given line is an executable Fortran line."""
    if CONT_PATTERN.match(prev_line):
        return False
    if NON_COMMENT_PATTERN.match(line) \
       and not USE_PATTERN.match(line) \
       and not VAR_PATTERN.match(line) \
       and not END_PATTERN.match(line) \
       and not IMPLICIT_PATTERN.match(line) \
       and not ELSE_PATTERN.match(line):
        return True
    else:
        return False


def match_line_number(filename, re_obj, start_line=1):
    """Return the line number matching the given regular expression."""
    with open(filename, "r") as fileobj:
        lineno = 0
        for line in fileobj:
            lineno += 1
            if lineno < start_line:
                continue
            match = re_obj.match(line)
            if match:
                return lineno
        raise Exception("Pattern not found: {0}".format(re_obj.pattern))


def calc_total_branch_rate(blocks):
    """Return total branch rate from given BLOCKS elements."""
    covered = 0
    total = 0
    for block in blocks:
        covered += int(block.get("covered", "0"))
        total += int(block.get("total", "0"))
    if total != 0:
        return covered/float(total)
    else:
        return 0


def module_to_class(module, source_path):
    """Convert MODULE element to a class element."""
    module_path = module.get("name", "unknown")
    module_name = os.path.join(source_path, module_path.split("/")[-1])
    branch_rate = str(calc_total_branch_rate(module.iter("BLOCKS")))
    class_elem = Element("class", attrib={"name": module_name,
                                          "branch-rate": branch_rate,
                                          "line-rate": branch_rate,
                                          "complexity": "0",
                                          "filename": module_name})
    methods = Element("methods")
    for function in module.findall("FUNCTION"):
        methods.append(function_to_method(function))
    class_elem.append(methods)
    return class_elem


def function_to_method(function):
    """Convert a FUNCTION element to a method element."""
    full_name = function.get("name", "unknown")
    function_name = full_name.split("_mp_")[-1].strip("_")
    blocks = function.find("BLOCKS")
    branch_rate = str(float(blocks.get("covered"))/float(blocks.get("total")))
    method = Element("method", attrib={"name": function_name,
                                       "branch-rate": branch_rate,
                                       "line-rate": branch_rate,
                                       "signature": ""})
    lines = Element("lines")
    for block in function.findall("BLOCK"):
        lines.append(block_to_line(block))
    method.append(lines)
    return method


def block_to_line(block):
    """Convert a BLOCK element to a line element."""
    block_instances = block.findall("INSTANCE")
    freq = str(max_instance_freq(block_instances))
    line_number = block.get("line", "0")
    line = Element("line", attrib={"hits": freq,
                                   "number": line_number})
    return line


def max_instance_freq(instances):
    """Return the maximum freq attribute in the given instances."""
    max_freq = 0
    for instance in instances:
        max_freq = max(int(instance.get("freq", "0")), max_freq)
    return max_freq


def read_xml_file(filename):
    """Return content of XML file."""
    with file(filename) as fileobj:
        xml_string = fileobj.read()
    return xml_string


def root_from_file(filename):
    """Return root element from given file."""
    import xml.etree.ElementTree as ET
    xml_string = read_xml_file(filename)
    root = ET.fromstring(xml_string)
    return root


def methods_in_file(filename):
    """Return a list of the method names in the given object file."""
    import subprocess
    try:
        nm_out = subprocess.check_output(["nm", "--defined-only",
                                          "-g", filename],
                                         stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError:
        return []
    functions = []
    for line in nm_out.splitlines():
        if is_nm_function(line):
            functions.append(function_name_from_nm_line(line))
    return functions


def is_nm_function(nm_line):
    """Return True if given nm_line describes a user-defined function."""
    parts = nm_line.split()
    if parts[2].endswith("._"):
        return False
#    if "___" in parts[2]:
#        return False
    type_letter = nm_line.split()[-2]
    return type_letter == "T"


def function_name_from_nm_line(nm_line):
    """Return function name from nm line, without module name."""
    function_name = nm_line.split()[-1]
    if function_name.find("_MOD_") != -1:
        function_name = function_name.split("_MOD_")[-1]
    if function_name.find("_mp_") != -1:
        function_name = function_name.split("_mp_")[-1]
    return function_name.strip("_")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Convert from Intel's "
                                     + "codecov XML format to Cobertura "
                                     + "XML format.")
    parser.add_argument('from_file',
                        help='Name of codecov XML file')
    parser.add_argument('source_path',
                        help='Relative path to source files')
    parser.add_argument('object_path',
                        help='Relative path to object files')
    parser.add_argument('to_file',
                        help='Name of (output) Cobertura XML file')
    parser.add_argument('--out-src-path', dest='out_src_path',
                        help='Relative path to source files to be used \
                        in output XML. This can be necessary if sources \
                        must be reported to reside in a different directory \
                        in order for Jenkins to distinguish between two XML \
                        files.', default=None)
    args = parser.parse_args()
    if args.out_src_path is None:
        args.out_src_path = args.source_path
    main(args.from_file, args.to_file, args.object_path, args.source_path,
         args.out_src_path)
