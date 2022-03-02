import unittest
from backup_checker import BackupChecker


class TestBackupChecker(unittest.TestCase):

    # alert levels
    # 0 - Verbose
    # 1 - Normal
    # 2 - Pass
    # 3 - Warning
    # 4 - Fail

    def test_known_good(self):
        checker = BackupChecker("/Volumes/CK_SSD/Sample footage/Test backups/0_Known_Good",
                                backup_trim=8, require_ale=True)

        self.assertFalse(checker.error_lock_triggered)
        self.assertEqual(checker.logger.alert_level, 2)

    def test_missing_backup_roll(self):
        checker = BackupChecker("/Volumes/CK_SSD/Sample footage/Test backups/1_Missing_Backup_Roll",
                                backup_trim=8, require_ale=True)

        self.assertTrue(checker.error_lock_triggered)
        self.assertEqual(checker.logger.alert_level, 4)

    def test_wrong_file_size(self):
        checker = BackupChecker("/Volumes/CK_SSD/Sample footage/Test backups/2_Wrong_File_Size",
                                backup_trim=8, require_ale=True)

        self.assertTrue(checker.error_lock_triggered)
        self.assertEqual(checker.logger.alert_level, 4)

    def test_missing_folder(self):
        checker = BackupChecker("/Volumes/CK_SSD/Sample footage/Test backups/3_Missing_Folder",
                                backup_trim=8, require_ale=True)

        self.assertFalse(checker.error_lock_triggered)
        self.assertEqual(checker.logger.alert_level, 3)

    def test_missing_ale(self):
        checker = BackupChecker("/Volumes/CK_SSD/Sample footage/Test backups/4_Missing_ALE",
                                backup_trim=8, require_ale=True)

        self.assertFalse(checker.error_lock_triggered)
        self.assertEqual(checker.logger.alert_level, 3)

        checker = BackupChecker("/Volumes/CK_SSD/Sample footage/Test backups/4_Missing_ALE",
                                backup_trim=8, require_ale=False)

        self.assertFalse(checker.error_lock_triggered)
        self.assertEqual(checker.logger.alert_level, 2)

    def test_missing_mhl(self):
        checker = BackupChecker("/Volumes/CK_SSD/Sample footage/Test backups/5_Missing_MHL",
                                backup_trim=8)

        self.assertFalse(checker.error_lock_triggered)
        self.assertEqual(checker.logger.alert_level, 3)

        checker = BackupChecker("/Volumes/CK_SSD/Sample footage/Test backups/5_Missing_MHL",
                                backup_trim=8, dual_backups=False)
        self.assertFalse(checker.error_lock_triggered)
        self.assertEqual(checker.logger.alert_level, 2)

