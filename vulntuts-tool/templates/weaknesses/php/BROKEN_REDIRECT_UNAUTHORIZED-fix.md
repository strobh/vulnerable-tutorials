The issue can be fixed by stopping the execution of the remaining PHP script with `exit;` after sending the `Location` header. This also stops any further content from being sent to the browser.

<pre class="language-php line-numbers" data-line="8"><code>
&lt;?php
// if the user is not logged in
if (!isset($_SESSION['user_id'])) {
    // redirect user to http://www.example.com/login.php
    header("Location: http://www.example.com/login.php");
    
    // very important! stop executing the code below
    exit;
}

// remaining code of the page
foobar(); // this code is not executed if the user is not logged in
?>

Some text that should only be sent to users who are logged in.
</code></pre>
