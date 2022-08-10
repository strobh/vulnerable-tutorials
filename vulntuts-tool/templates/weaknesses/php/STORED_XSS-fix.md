The function `htmlspecialchars` converts any HTML special characters into their HTML encodings, meaning they will then *not* be processed as standard HTML.

As a general rule, you should **never trust input coming from a client**. Every GET or POST parameter and cookie value should therefore be validated. Even in smaller applications data is moved around and it is not always clear whether the data came from a user or not. Therefore, it is best practice to **always escape any output** so they will not be evaluated in an unexpected way. 

To fix the example from the previous section:

<pre class="language-php line-numbers" data-line="9-10"><code>
$product_id = $_GET["product_id"];

// load reviews for the product
$stmt = $conn->prepare("SELECT * FROM reviews WHERE product_id = :product_id");
$stmt->bindParam(':product_id', $product_id);
$stmt->execute();
while ($row = $stmt->fetch()) {
    echo "&lt;p>";
    echo htmlspecialchars($row['author']) . " has written:&lt;br />";
    echo htmlspecialchars($row['review']);
    echo "&lt;/p>";
}
</code></pre>

The resulting HTML of the web page would then look like this:

<pre class="language-html line-numbers"><code>
&lt;p>
reviewer1 has written:&lt;br />
Awesome product!
&amp;lt;script&amp;gt;
alert(&amp;quot;Malicious code&amp;quot;);
&amp;lt;/script&amp;gt;
&lt;/p>
</code></pre>

And would be displayed in the browser like this:

<pre class="language-html line-numbers"><code>
reviewer1 has written:
Awesome product!
&lt;script&gt;
alert(&quot;Malicious code&quot;);
&lt;/script&gt;
</code></pre>

The script tag will not be interpreted as a JavaScript tag by the browser, but instead as simple text.
