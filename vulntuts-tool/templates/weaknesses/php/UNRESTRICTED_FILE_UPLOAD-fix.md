Each file that is uploaded to the server should be validated.

The software should not only check the file extension, but preferably also the **content or MIME type of the file** (for example, whether the file is a valid image if an image is to be uploaded), since the file extension can be manipulated.
Furthermore, the software should also check the **size of the file**.

Ideally, the file should be given a randomly generated filename instead of the original filename. This may also help to prevent a user from accidentally overwriting an existing file.
If the original file name has to be used, it must be ensured that only **valid characters are contained in the file name**. Otherwise, path traversal attacks are possible that allow an attacker to place the file at a different path than the intended one.

To fix the example from the previous section:

<pre class="language-php line-numbers"><code>
function upload_file() {
    $target_dir = "uploads/";
    $target_file = $target_dir . basename($_FILES["file"]["name"]);

    $check = getimagesize($_FILES["file"]["tmp_name"]);
    if ($check == false) {
        echo "The file is not an image.";
        return;
    }

    if (file_exists($target_file)) {
        echo "The file already exists.";
        return;
    }

    // check file size to be smaller than 10 MB
    if ($_FILES["file"]["size"] > 1024 * 1024 * 10) {
        echo "The file is too large.";
        return;
    }

    if (move_uploaded_file($_FILES["file"]["tmp_name"], $target_file)) {
        echo "The file ". htmlspecialchars(basename($_FILES["file"]["name"])). " has been uploaded.";
    } else {
        echo "There was an error uploading your file.";
    }
}
</code></pre>
