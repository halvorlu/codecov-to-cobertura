#!/usr/bin/env python2
import codecov_to_cobertura as ctc
import unittest


class TestCodecovToCobertura(unittest.TestCase):
    """Test codecov_to_cobertura.py"""

    def test_is_executable_line(self):
        from codecov_to_cobertura import is_executable_line
        self.assertFalse(is_executable_line('      !a=1'))
        self.assertFalse(is_executable_line('           '))
        self.assertFalse(is_executable_line('  continued line',
                                            'first line&'))
        self.assertFalse(is_executable_line(' use module'))
        self.assertFalse(is_executable_line(' real :: a'))
        self.assertFalse(is_executable_line(' enddo'))
        self.assertFalse(is_executable_line(' endif'))
        self.assertFalse(is_executable_line(' implicit none'))
        self.assertFalse(is_executable_line(' real, dimension(1:2) :: a'))
        self.assertFalse(is_executable_line(' end function foo'))
        self.assertFalse(is_executable_line(' end subroutine bar'))
        self.assertFalse(is_executable_line(' contains'))

        self.assertTrue(is_executable_line(' function a'))
        self.assertTrue(is_executable_line(' subroutine b'))
        self.assertTrue(is_executable_line(' a = b + c'))
        self.assertTrue(is_executable_line(' call b ! comment'))
        self.assertTrue(is_executable_line(' a = 2 ! real :: a'))


if __name__ == "__main__":
    unittest.main()
