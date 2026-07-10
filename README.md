# My Setlists

## Setup

1. Clone the repository
2. Create and activate a Python virtual environment
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy the example environment file and fill in the database credentials:
   ```bash
   cp .env.example .env
   ```

## Running the application

Start the database and other services with Docker Compose:
```bash
docker compose up
```

Then run the FastAPI app in a separate terminal:
```bash
python main.py
```

## Testing

Run the test suite:
```bash
python -m pytest tests/ -v
```

Run a specific test file:
```bash
python -m pytest tests/test_users.py -v
```

The test suite includes:
- **test_users.py**: User authentication, profile management, and cascade deletion
- **test_songs.py**: Song CRUD operations and setlist associations
- **test_setlists.py**: Setlist management, song addition/removal, and access control

All tests use an in-memory SQLite database for isolation and speed (16 tests pass in ~0.5s).

## Architecture

### Database Relationships & Cascade Delete

The application uses SQLAlchemy 2.0's cascade delete functionality to automatically clean up related records:

- **User → Setlists**: When a user is deleted, all their setlists are automatically deleted
- **Setlist → SetlistEntries**: When a setlist is deleted, all song entries are automatically removed
- **Song → SetlistEntries**: When a song is deleted, all its entries across setlists are cleaned up

This eliminates the need for manual cascading deletes in route handlers.

### Type Safety with SQLAlchemy 2.0 & SQLModel

Models use `Mapped` type annotations from SQLAlchemy 2.0 combined with Pydantic for full type safety:

```python
from typing import Optional, TYPE_CHECKING
from sqlalchemy.orm import Mapped
from sqlmodel import SQLModel, Relationship

if TYPE_CHECKING:
    from .user import User

class Setlist(SQLModel, table=True):
    id: int | None = None
    user_id: int | None = None
    user: Mapped[Optional["User"]] = Relationship(back_populates="setlists")
```

Key patterns:
- **Forward references** use `Optional["ClassName"]` (not `"ClassName" | None`) to work with `Mapped` types
- **TYPE_CHECKING guards** prevent circular imports between related models
- **Cascade configuration** is defined via `sa_relationship_kwargs` on relationship fields

## Database Schema

The database schema is shown below. The diagram was generated with dbdiagram.io:

- Diagram link: https://dbdiagram.io/d/MySetlists-6a3969b39340ecc065ef0adf

![Database schema](docs/my-setlists-schema.png)