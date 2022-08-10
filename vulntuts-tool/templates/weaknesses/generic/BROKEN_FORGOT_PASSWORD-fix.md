The preferred way is to implement the `forgot password` mechanism as explained in the previous section.

The following short guidelines can be used as a quick reference to protect the forgot password service (source: [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html)):

- Return a consistent message for both existent and non-existent accounts.
- Use a side-channel (e.g., emails) to communicate the method to reset the password.
- Use URL tokens for the simplest and fastest implementation.
- Ensure that generated tokens or codes are:
    - Randomly generated using a cryptographically safe algorithm.
    - Sufficiently long to protect against brute-force attacks.
    - Stored securely.
    - Single use and expire after an appropriate period.
- Do not make a change to the account until a valid token is presented, such as locking out the account.
