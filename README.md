# Goals
This project consists of a weather monitor, that reades real time data from measuring devices, and saves it to
the database.


## Understandings & TODO (Omer)
This project uses Python 3.8.10 
When developing one should create a local env for testing. And use one of the staging machines for active development instead of production.

We should consider moving to a newer python version. 3.8's EOL was in 2024. If we move, we should go for 3.13 as EOL is in 2029.
This would allow usage of new features and others. Since it's a venv we don't need to worry about compat issues.



### Trying with 3.8
Live as well in case db falls
### Consider moving to a VENV
This can isolate issues to a specific env. i.e. each script will run in it's own version and we don't experience issue between scripts.

## Tasks

Create a live & fallback in-case the DB fails. (We store the info in an alternate format. i.e. csv)
Then import when the db fails.

It is important that each sensor works standalone as well as a part of the other system.
