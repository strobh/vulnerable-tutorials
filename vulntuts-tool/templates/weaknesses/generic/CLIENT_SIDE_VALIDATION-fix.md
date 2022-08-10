As a general rule, you should **never trust input coming from a client**. The **server software** should, therefore, **validate every GET or POST parameter and cookie value**.

Validation on the client should only be seen as a feature that allows users to get feedback without having to send the data to the server first. However, client-side validation is in no way intended to protect the server.
