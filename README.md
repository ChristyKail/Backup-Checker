# CFD Backup Checker
This tool is designed to check that backups are complete. It does this by checking the every MHL entry from the original folders is present in the backup MHL or MHLs. 
Additionally, it can check that every clip referenced in an ALE is also present in that backup MHL.

##Requirements:
 - Python3 (tested on 3.9)
 - Tkinter for Python3 
 - Pandas

##Installation
Download the source code, unzip the package, and run the `backup_checker.py` script by running `python3 backup_checker.py`

<img alt="Main window" height="500" src="https://imgur.com/s5veD9s"/>

##Basic operation
 - Place your backup MHLs and delivery ALE in a `Verifier` folder inside the day folder you want to check.
 - Choose the preset for your job format from the dropdown menu.
 - Click `Select folder` and choose the day folder you wish to check.
 - Wait while checks are performed. Information about the operation will be shown on the console.
 - When complete, the name of the day folder will be displayed in either green, orange, or red, and a report will be written to the day folder.
 - Green means the checks completed successfully
 - Red means either files were missing from the backup or were the wrong size on the backup.
 - Orange means there were some warnings raised during the checks, and not all files may have been checked completely.
 
##Creating job formats
Job format presets are stored in the `presets.csv` file, next to the tool. You can fill in a new row to create a new job format as follows:
 - **Name** - The name of the job format
 - **Backup Pattern** - the REGEX pattern used to trim the backup file paths (see path normalization below)
 - **Backup Trim** - the number of levels to trim off the beginning of the backup file paths(see path normalization below)
 - **Dual Backup** - Whether to expect primary (odd) and secondary (even) LTO backup numbers - 0 for No, 1 for Yes
 - **Add roll folder** - Whether to add the roll folder names to the root of source file paths - 0 for No, 1 for Yes
 - **Source A-D** - Names of folders to scan for source MHLs, usually 'Camera_Media' and 'Sound_Media'
 - **Require ALE** - Whether to expect a delivery ALE to check. The tool will always check against an ALE if one is available, but if this is enabled it will warn if it can't find one - 0 for No, 1 for Yes.

##Folder Layout
  - The two source MHLs (created by Silverstack) are left in place, in the `Camera_Media` and `Sound_Media` folders. These folders are defined in the job format preset
  - The backup MHLs (Created by YoYotta) and optionally a delivery ALE are placed in a `Verifier` folder. Alternatively, they can be placed in the level above (`TEST_DAY_001`). The tool will always default to using the `Verifier` folder.
  
 <img alt="Main window" height="500" src="https://imgur.com/XCoHuxu"/>

##Path normalization 
In the example above, the source MHL and backup MHL will use different paths to refer to the same files:
 - Source MHL - `M002C001_161207_R00H.mxf`
 - Backup MHL - `/Volumes/LTO001/TESTS/TEST_DAY_001/Camera_Media/M002R00H/M002C001_161207_R00H.mxf`

This is where the **Backup Pattern**, **Backup Trim**, and **Add Roll Folder** options in the job preset come in to play.

**Add Roll Folder** will add the source MHL's folder to its file paths, resulting in `M002R00H/M002C001_161207_R00H.mxf`

The **Backup Trim** value will remove that number of elements from the backup MHL file paths, for example setting it to `5` in this case will result in `/M002R00H/M002C001_161207_R00H.mxf` as the first five levels have been trimmed.
If you set this to more levels than are present in the given path (in this case setting it to `7` or more) an error will be thrown.

**Backup Patten** can be used on more complex paths to trim based on a regular expression. For example the same result as before can be achieved by setting **Backup Pattern** for `Camera_Media` or `_Media`.
This will trim everything above the folder that matches the regular expression.

Note - **Backup Pattern** and **Backup Trim** can be used in conjunction with each other, for example setting them to `TEST_DAY_\d{3}` and `1` will have the same result again.

Note - Using regular expressions is much more computationally expensive than just using the trim, so should be avoided wherever possible.

##Fail cases
The tool will report "Failed" in the following cases:
 - An index in the located source MHLs is missing in one or more of the backups
 - An index in the located source MHLs has a different file size in one or more of the backups
 - A clip in the located delivery ALE is not in one or more of the backups (for file-per-frame media only the first frame of each clip will be checked)

The tool will report "Warning" in the following cases:
 - One or more of the source folders specified in the job format can't be found and scanned for MHLs.
 - There is no delivery ALE located, when one was expected. Checks will continue based on source MHLs only.
 - One or more of the backup MHLs can't be categorised. Checks will continue, but if you've specified dual backups, don't assume MHLs have been split into primary and secondary properly.
 - Only one backup was found when dual backups have been specified
 - The number of files referenced in the source MHLs doesn't the actual number of source files. It may be that some files were deleted, or that a source MHL is missing. Any clips that on a missing source MHL can't be checked.
