CRLF injection attacks in email headers can be prevented by validating the user input that is used in the email header. The software should **prohibit the use of any newline characters in the input**.

To validate an email address before it is used in the email header, the `filter_var()` function in PHP can be used:

<pre class="language-php line-numbers" data-line="1-2"><code>
if (!filter_var($_POST['email'], FILTER_VALIDATE_EMAIL)) {
    echo "The email address is invalid.";
}
else {
    $headers = "From: " . $_POST['email'] . "\r\n";
    mail("contact@example.org", $_POST['subject'], $_POST['text'], $headers);
}
</code></pre>

If the email specified by the user contains a line break, the script considers this email invalid and prints an error message. The email is not sent.
