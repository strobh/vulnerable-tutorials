The function `htmlspecialchars` converts any HTML special characters into their HTML encodings, meaning they will then *not* be processed as standard HTML.

As a general rule, you should **never trust input coming from a client**. Every GET or POST parameter and cookie value should therefore be validated. Therefore, it is best practice to **always escape any output** so they will not be evaluated in an unexpected way. 

To fix the example from the previous section:

<pre class="language-php line-numbers"><code>
echo "&lt;p>" . htmlspecialchars($_GET["message"]) . "&lt;/p>";
</code></pre>

The resulting HTML of the web page would then look like this:

<pre class="language-html line-numbers"><code>
&lt;p>Some message!&amp;lt;script&amp;gt;alert(&amp;quot;Malicious code&amp;quot;);&amp;lt;/script&amp;gt;&lt;/p>
</code></pre>

And would be displayed in the browser like this:

<pre class="language-html line-numbers"><code>
Some message!&lt;script&gt;alert(&quot;Malicious code&quot;);&lt;/script&gt;
</code></pre>

The script tag will not be interpreted as a JavaScript tag by the browser, but instead as simple text.
