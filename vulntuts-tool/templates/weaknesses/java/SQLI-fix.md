The most secure and modern approach is to use **prepared statements**.

<pre class="language-java line-numbers" data-line="21-23"><code>
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.Statement;

public class SQLDemo {
   public static void main(String[] args) {
        // connect to database
        Connection connection = DriverManager.getConnection(
            "jdbc:mysql://localhost:3306/db_name",
            "db_username", 
            "db_password"
        );

        // username and password entered by the user
        String username = "foo";
        String password = "bar";

        String query = "SELECT * FROM users WHERE name = ? AND password = ?";
        PreparedStatement stmt = connection.prepareStatement(query);
        stmt.setString(1, username);
        stmt.setString(2, password);

        ResultSet result = stmt.executeQuery();

        if (result.next()) {
            System.out.println("successfully logged in");
        }
        else {
            System.out.println("wrong username or password");
        }
    }
}
</code></pre>

Prepared statements make a strict distinction between the query and the data to be used in the query. In the query, the `?` marks where the data should be inserted later. Afterwards, we supply the values using the method  `stmt.setString()`. The database takes care that the data is always interpreted as data only. Manipulation of the query is thus no longer possible.
