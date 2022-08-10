The most secure and modern approach is to use **prepared statements**.

<pre class="language-php line-numbers" data-line="5-7"><code>
$username = $_POST["username"];
$password = $_POST["password"];

$pdo = new PDO("mysql:host=localhost;dbname=database", $username, $password);
$stmt = $conn->prepare("SELECT * FROM users WHERE name = :username AND password = :password");
$stmt->bindParam(':username', $username);
$stmt->bindParam(':password', $password);
$stmt->execute();
</code></pre>

Prepared statements make a strict distinction between the query and the data to be used in the query. In the query, `:username` and `:password` marks where the data should be inserted later. Afterwards, we supply the values using the method  `bindParam()`. The database takes care that the data is always interpreted as data only. Manipulation of the query is thus no longer possible.

For more information about prepared statements, see: [PHP manual for `PDO::prepare`](https://www.php.net/manual/de/pdo.prepare.php) or [other prevention techniques provided by the OWASP Foundation](https://owasp.org/Top10/A03_2021-Injection/#how-to-prevent).
