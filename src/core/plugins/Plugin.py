#!/usr/bin/env python3

#            ---------------------------------------------------
#                              Omega Framework                                
#            ---------------------------------------------------
#                  Copyright (C) <2020>  <Entynetproject>       
#
#        This program is free software: you can redistribute it and/or modify
#        it under the terms of the GNU General Public License as published by
#        the Free Software Foundation, either version 3 of the License, or
#        any later version.
#
#        This program is distributed in the hope that it will be useful,
#        but WITHOUT ANY WARRANTY; without even the implied warranty of
#        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#        GNU General Public License for more details.
#
#        You should have received a copy of the GNU General Public License
#        along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import importlib
import importlib.machinery
import traceback

from datatypes import Path
from ui.color import colorize

from .exceptions import BadPlugin


# pylint: disable=too-few-public-methods
class Plugin:
    """Omega plugin class

    This object instanciates a new plugin object.

    Example:
    >>> plugin = Plugin("./plugins/file_system/ls")
    >>> plugin.name
    'ls'
    >>> plugin.category
    'File system'
    >>> plugin.run(['ls', '-la'])  # run the plugin with args

    """

    def __init__(self, path):
        if path.endswith(os.sep) or path.endswith("/"):
            path = path[:-1]
        self.path = path
        self.name = os.path.basename(path)
        self.argv = [] # redefined at runtime on run()

        try:
            Path(path, mode='drx')()
        except ValueError as e:
            print("[v] Couldn't load plugin: «%s»" % self.path)
            print("[v]     Plugin directory error: %s" % e)
            print("[v] ")
            raise BadPlugin

        category = os.path.basename(os.path.dirname(path))
        self.category = category.replace("_", " ").capitalize()

        self.help = ""
        try:
            script = Path(self.path, "plugin.py", mode='fr').read()
        except ValueError as e:
            print("[v] Couldn't load plugin: «%s»" % self.path)
            print("[v]     File error on plugin.py: %s" % e)
            print("[v] ")
            raise BadPlugin
        if not script.strip():
            print("[v] Couldn't load plugin: «%s»" % self.path)
            print("[v]     File plugin.py is empty")
            print("[v] ")
            raise BadPlugin
        try:
            code = compile(script, "", "exec")
        except BaseException as e:
            print("[v] Couldn't compile plugin: «%s»" % self.path)
            e = traceback.format_exception(type(e), e, e.__traceback__)
            for line in "".join(e).splitlines():
                print(colorize("[v] ", "%Red", line))
            # print("[v] " + "\n[v] ".join("".join(e).splitlines()))
            print("[v] ")
            raise BadPlugin
        if "__doc__" in code.co_names:
            self.help = code.co_consts[0]

    def run(self, argv):
        """run current plugin
        """
        self.argv = argv
        from api import server
        try:
            ExecPlugin(self)
        except KeyboardInterrupt:
            raise KeyboardInterrupt
        except SystemExit as e:
            retval = e.args[0] if e.args else e.code
            if not isinstance(retval, int):
                lines = self.help.splitlines()
                if len(lines) > 1 and str(retval) == self.help:
                    print()
                    print("[*] %s: %s" % (self.name, lines.pop(0)))
                    for line in lines:
                        if line == line.lstrip():
                            line = colorize("%BoldWhite", line)
                        print(line)
                    print()
                else:
                    print("[!] %s: %s" % (self.name, retval))
                retval = 1
            return retval
        except server.payload.PayloadError as err:
            print("[!] %s: %s" % (self.name, err))
            return 64
        except BaseException as err:
            msg = "Python runtime error (exception occured)"
            print("[!] %s: %s:" % (self.name, msg))
            raise err
        return 0


class ExecPlugin:
    """Execute an Omega plugin
    """
    filename = "plugin"
    _instance_id = 0

    def __init__(self, plugin):
        script_path = os.path.join(plugin.path, self.filename + ".py")
        sys.path.insert(0, plugin.path)
        try:
            self.exec_module(script_path)
        finally:
            sys.path.pop(0)

    @classmethod
    def is_first_instance(cls):
        """check whether current instance is the first loaded one
        """
        result = not cls._instance_id
        cls._instance_id += 1
        return result

    def exec_module(self, path):
        """execute plugin as an `importlib` module
        """
        loader = importlib.machinery.SourceFileLoader(self.filename, path)
        module = importlib.import_module(self.filename)

        # If the instance is the first one, it means that
        # the import already executed the plugin.
        if not self.is_first_instance():
            loader.exec_module(module)
