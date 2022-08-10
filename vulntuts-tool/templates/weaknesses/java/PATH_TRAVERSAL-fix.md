The preferred solution is to **not use user input when creating file paths**. Instead, the software could use randomly generated file names and the user could address these files via an ID that is easier to validate.
Alternatively, you should consider a white-listing approach, where a **set of filenames is defined as valid and everything else is considered invalid**.
If you are forced to use user input for file operations, **validate and normalize the input** before using it.

**Warning**: Do not rely on removing `../` or blacklisting certain characters from the user input as there are many ways to bypass this kind of protection. For example, if the user input is `....//file.txt` and the software removes the string `../` the resulting string is `../file.txt`.

The following example fixes the issue from the previous section by using a file ID (that must be an integer) instead of a file name:

<pre class="language-java line-numbers"><code>
import java.io.*;
import javax.servlet.*;
import javax.servlet.http.*;
import javax.servlet.annotation.*;

@WebServlet("/download")
public class DownloadServlet extends HttpServlet {
    private final int ARBITARY_SIZE = 1048;

    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) 
        throws ServletException, IOException
    {
        String fileId = request.getParameter("fileId");
        if (fileId == null or !fileId.matches("\\d+")) {
            resp.getWriter().print("Please supply a valid filde Id");
            return;
        }

        // load the file name, e.g., from a database
        String fileName = load_file_name_by_id(fileId);
    
        resp.setContentType("text/plain");
        resp.setHeader("Content-disposition", "attachment; filename=" + fileName);

        try(InputStream in = req.getServletContext().getRealPath("/").getResourceAsStream(fileName);
            OutputStream out = resp.getOutputStream()) {

            byte[] buffer = new byte[ARBITARY_SIZE];
        
            int numBytesRead;
            while ((numBytesRead = in.read(buffer)) > 0) {
                out.write(buffer, 0, numBytesRead);
            }
        }
    }
}
</code></pre>
