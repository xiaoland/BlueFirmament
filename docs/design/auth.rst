Auth Design
===========

BlueFirmament auth(enticattion, orization) design document.

This document describes the design of auth module.

Auth module provide a unified interface for authentication,
authorization and access control to DAL.

AuthProvider
------------
- SignUp User
- Login (Authenticate) User and authorize (give session)
- Thrid-Party Authentication source

With Scheme
-----------
Filter fields from being get, set by users of some roles.
(CLS is not a good solution for this case)

