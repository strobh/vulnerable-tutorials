After a successful login, the server could store whether the user is logged in, for example, by storing the user's ID in the session:

<pre class="language-php line-numbers"><code>
// login was successful
$_SESSION['user_id'] = $ID_OF_THE_USER;
</code></pre>

On the page that should only be accessible by a logged-in user, the server would then be able to check whether this variable is set:

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

If the user is not logged in, he will be redirected to the login page. This is accomplished by sending the HTTP header `Location` that signals the browser to load another page.
After sending the `Location` header, however, the rest of the code would still be executed (`foobar()`) and the page content is also sent to the browser (`Some text that should only be sent to users who are logged in.`).
The user usually does not notice this, because the browser immediately loads the login page. However, an attacker receives the content from the server and can view it without any problems.

Therefore, it is very important that the **execution of the remaining code is stopped by terminating the script** with `exit;`.

Finally, note that the variable `$_SESSION['user_id']` must be deleted when the user logs off:

<pre class="language-php line-numbers"><code>
// after user has logged out:
unset($_SESSION['user_id']);
</code></pre>
