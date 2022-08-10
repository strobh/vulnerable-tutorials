The OTP secret should be generated randomly for each user and saved in the database:

<pre class="language-php line-numbers"><code>
$auth = new \Sonata\GoogleAuthenticator\GoogleAuthenticator();

$username = "..."; // username
$issuer = "..."; // name of the website/issueer
$secret = $auth->generateSecret();

$url = $auth->getURL($username, $issuer, $secret);

// TODO: save secret to database
</code></pre>
