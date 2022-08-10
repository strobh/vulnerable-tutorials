Each file that is uploaded to the server should be validated.

The software should not only check the file extension, but preferably also the **content or MIME type of the file** (for example, whether the file is a valid image if an image is to be uploaded), since the file extension can be manipulated.
Furthermore, the software should also check the **size of the file**.

Ideally, the file should be given a randomly generated filename instead of the original filename. This may also help to prevent a user from accidentally overwriting an existing file.
If the original file name has to be used, it must be ensured that only **valid characters are contained in the file name**. Otherwise, path traversal attacks are possible that allow an attacker to place the file at a different path than the intended one.

To fix the example from the previous section using the `magic` library:

<pre class="language-python line-numbers"><code>
import cgi, os
import cgitb
cgitb.enable()
import magic

form = cgi.FieldStorage()
fileitem = form['filename']

# check if the file has been uploaded
if fileitem.filename:
    # strip the leading path from the file name
    filename = os.path.basename(fileitem.filename)

    if magic.from_buffer(fileitem.file.read(), mime=True) != 'image/jpeg':
        print("The file must be a jpeg.")
    else:
        # write the file to the server
        open("uploads/" + filename, 'wb').write(fileitem.file.read())
</code></pre>
