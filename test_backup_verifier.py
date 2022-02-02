import unittest
import backup_verifier


class TestBackup(unittest.TestCase):

    def setUp(self):
        pass

    def test_known_good(self):
        test_verifier = backup_verifier.BackupVerifier("/Users/christykail/Sample footage/Test backups/0_Known_Good")

        self.assertEqual(len(test_verifier.backups), 1)

        test_verifier.run_checks()
        report, checks_passed = test_verifier.write_report(skip_writing_file=True)
        test_backup = test_verifier.backups[0]

        self.assertEqual(len(test_backup.source_index) + len(test_backup.source_mhls), 18)

        self.assertEqual(len(test_backup.source_i_missing_in_backup_i), 0)
        self.assertEqual(len(test_backup.source_i_wrong_in_backup_i), 0)
        self.assertEqual(len(test_backup.source_f_missing_in_backup_i), 0)
        self.assertEqual(len(test_backup.source_i_missing_in_source_f), 0)
        self.assertEqual(len(test_backup.source_f_missing_in_source_i), 0)

        self.assertTrue(test_backup.checks_passed())
        self.assertTrue(checks_passed)

    def test_missing_backup(self):
        test_verifier = backup_verifier.BackupVerifier(
            "/Users/christykail/Sample footage/Test backups/1_Missing_Backup_Roll")

        self.assertEqual(len(test_verifier.backups), 1)

        test_verifier.run_checks()
        report, these_checks_passed = test_verifier.write_report(skip_writing_file=True)
        test_backup = test_verifier.backups[0]

        self.assertEqual(len(test_backup.source_index) + len(test_backup.source_mhls), 18)

        self.assertEqual(len(test_backup.source_i_missing_in_backup_i), 9)
        self.assertEqual(len(test_backup.source_i_wrong_in_backup_i), 0)
        self.assertEqual(len(test_backup.source_f_missing_in_backup_i), 10)
        self.assertEqual(len(test_backup.source_i_missing_in_source_f), 0)
        self.assertEqual(len(test_backup.source_f_missing_in_source_i), 0)

        self.assertFalse(test_backup.checks_passed())
        self.assertFalse(these_checks_passed)

    def test_wrong_file_size(self):
        test_verifier = backup_verifier.BackupVerifier("/Users/christykail/Sample footage/Test backups/2_Wrong_File_Size")

        self.assertEqual(len(test_verifier.backups), 1)

        test_verifier.run_checks()
        report, checks_passed = test_verifier.write_report(skip_writing_file=True)
        test_backup = test_verifier.backups[0]

        self.assertEqual(len(test_backup.source_index) + len(test_backup.source_mhls), 18)

        self.assertEqual(len(test_backup.source_i_missing_in_backup_i), 0)
        self.assertEqual(len(test_backup.source_i_wrong_in_backup_i), 1)
        self.assertEqual(len(test_backup.source_f_missing_in_backup_i), 0)
        self.assertEqual(len(test_backup.source_i_missing_in_source_f), 0)
        self.assertEqual(len(test_backup.source_f_missing_in_source_i), 0)

        self.assertFalse(test_backup.checks_passed())
        self.assertFalse(checks_passed)

    def test_unindexed_files(self):
        test_verifier = backup_verifier.BackupVerifier("/Users/christykail/Sample footage/Test backups/3_Unindexed_Files")

        self.assertEqual(len(test_verifier.backups), 1)

        test_verifier.run_checks()
        report, checks_passed = test_verifier.write_report(skip_writing_file=True)
        test_backup = test_verifier.backups[0]

        self.assertEqual(len(test_backup.source_index) + len(test_backup.source_mhls), 8)

        self.assertEqual(len(test_backup.source_i_missing_in_backup_i), 0)
        self.assertEqual(len(test_backup.source_i_wrong_in_backup_i), 0)
        self.assertEqual(len(test_backup.source_f_missing_in_backup_i), 0)
        self.assertEqual(len(test_backup.source_i_missing_in_source_f), 0)
        self.assertEqual(len(test_backup.source_f_missing_in_source_i), 9)

        self.assertFalse(test_backup.checks_passed())
        self.assertFalse(checks_passed)

    def test_deleted_file(self):
        test_verifier = backup_verifier.BackupVerifier("/Users/christykail/Sample footage/Test backups/4_File_Deleted")

        self.assertEqual(len(test_verifier.backups), 1)

        test_verifier.run_checks()
        report, checks_passed = test_verifier.write_report(skip_writing_file=True)
        test_backup = test_verifier.backups[0]

        self.assertEqual(len(test_backup.source_index) + len(test_backup.source_mhls), 18)

        self.assertEqual(len(test_backup.source_i_missing_in_backup_i), 0)
        self.assertEqual(len(test_backup.source_i_wrong_in_backup_i), 0)
        self.assertEqual(len(test_backup.source_f_missing_in_backup_i), 0)
        self.assertEqual(len(test_backup.source_i_missing_in_source_f), 1)
        self.assertEqual(len(test_backup.source_f_missing_in_source_i), 0)

        self.assertFalse(test_backup.checks_passed())
        self.assertFalse(checks_passed)


if __name__ == '__main__':
    unittest.main()
