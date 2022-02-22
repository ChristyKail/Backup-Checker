import unittest
import mhl_backup_comparison


class TestBackup(unittest.TestCase):

    def setUp(self):
        pass

    def test_known_good(self):

        preset = mhl_backup_comparison.load_presets('presets.csv')

        test_verifier = mhl_backup_comparison.make_checker_from_preset(
            "/Volumes/CK_SSD/Sample footage/Test backups/0_Known_Good", 'Tests', preset)

        self.assertEqual(test_verifier.checks_run, True)
        self.assertEqual(test_verifier.checker_passed, True)
        self.assertEqual(len(test_verifier.backups), 2)

    def test_missing_roll(self):

        preset = mhl_backup_comparison.load_presets('presets.csv')

        test_verifier = mhl_backup_comparison.make_checker_from_preset(
            "/Volumes/CK_SSD/Sample footage/Test backups/1_Missing_Backup_Roll", 'Tests', preset)

        self.assertEqual(test_verifier.checks_run, True)
        self.assertEqual(test_verifier.checker_passed, False)
        self.assertEqual(len(test_verifier.backups), 2)

    def test_wrong_file_size(self):

        preset = mhl_backup_comparison.load_presets('presets.csv')

        test_verifier = mhl_backup_comparison.make_checker_from_preset(
            "/Volumes/CK_SSD/Sample footage/Test backups/2_Wrong_File_Size", 'Tests_Single', preset)

        self.assertEqual(test_verifier.checks_run, True)
        self.assertEqual(test_verifier.checker_passed, False)
        self.assertEqual(len(test_verifier.backups), 1)


if __name__ == '__main__':

    unittest.main()
