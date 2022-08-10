Each file that is uploaded to the server should be validated.

The software should not only check the file extension, but preferably also the **content or MIME type of the file** (for example, whether the file is a valid image if an image is to be uploaded), since the file extension can be manipulated.
Furthermore, the software should also check the **size of the file**.

Ideally, the file should be given a randomly generated filename instead of the original filename. This may also help to prevent a user from accidentally overwriting an existing file.
If the original file name has to be used, it must be ensured that only **valid characters are contained in the file name**. Otherwise, path traversal attacks are possible that allow an attacker to place the file at a different path than the intended one.

How validation is implemented in code depends very much on the framework used. Therefore, no code is presented here.
