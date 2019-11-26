#  NanoVNASaver - a python program to view and export Touchstone data from a NanoVNA
#  Copyright (C) 2019.  Rune B. Broberg
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

import sys
import unittest


###############################################################################
#
# Executing this file initiates the discovery and execution of all unittests
# in the "test" directory, with filenames starting with "test" that have a
# TestCases(unittest.TestCase) Class, which has class functions starting with
# "test_". This provides a simple test framework that is easily expandable by
# simply adding new "test_xxx.py" files into the test directory.
#
###############################################################################

if __name__ == '__main__':
    sys.path.append('.')
    loader = unittest.TestLoader()
    tests = loader.discover('.')
    testRunner = unittest.runner.TextTestRunner(
        failfast=False,
        verbosity=2)
    testRunner.run(tests)
