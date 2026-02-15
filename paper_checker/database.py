"""
Database operations for storing and querying papers.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from paper_checker.models import Paper, AccessibilityStatus, ResourceType


class PaperDatabase:
    """SQLite database for storing paper information"""
    
    def __init__(self, db_path: str = "papers.db"):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.connection = None
        self._init_database()
    
    def _init_database(self):
        """Initialize database and create tables if they don't exist"""
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        
        cursor = self.connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS papers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                authors TEXT,
                year INTEGER,
                resource_type TEXT,
                doi TEXT,
                url TEXT,
                arxiv_id TEXT,
                journal TEXT,
                conference TEXT,
                publisher TEXT,
                volume TEXT,
                issue TEXT,
                pages TEXT,
                accessibility_status TEXT,
                last_checked TEXT,
                download_url TEXT,
                requires_authentication INTEGER,
                authentication_service TEXT,
                local_file_path TEXT,
                abstract TEXT,
                keywords TEXT,
                notes TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        # Create indexes for common queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_papers_title ON papers(title)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_papers_accessibility ON papers(accessibility_status)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_papers_doi ON papers(doi)
        """)
        
        self.connection.commit()
    
    def add_paper(self, paper: Paper) -> int:
        """
        Add a new paper to the database.
        
        Args:
            paper: Paper object to add
            
        Returns:
            ID of the inserted paper
        """
        cursor = self.connection.cursor()
        now = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO papers (
                title, authors, year, resource_type, doi, url, arxiv_id,
                journal, conference, publisher, volume, issue, pages,
                accessibility_status, last_checked, download_url,
                requires_authentication, authentication_service, local_file_path,
                abstract, keywords, notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            paper.title,
            json.dumps(paper.authors),
            paper.year,
            paper.resource_type.value if paper.resource_type else None,
            paper.doi,
            paper.url,
            paper.arxiv_id,
            paper.journal,
            paper.conference,
            paper.publisher,
            paper.volume,
            paper.issue,
            paper.pages,
            paper.accessibility_status.value if paper.accessibility_status else None,
            paper.last_checked.isoformat() if paper.last_checked else None,
            paper.download_url,
            1 if paper.requires_authentication else 0,
            paper.authentication_service,
            paper.local_file_path,
            paper.abstract,
            json.dumps(paper.keywords),
            paper.notes,
            now,
            now
        ))
        
        self.connection.commit()
        return cursor.lastrowid
    
    def get_paper(self, paper_id: int) -> Optional[Paper]:
        """
        Get a paper by ID.
        
        Args:
            paper_id: ID of the paper
            
        Returns:
            Paper object or None if not found
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM papers WHERE id = ?", (paper_id,))
        row = cursor.fetchone()
        
        if row:
            return self._row_to_paper(row)
        return None
    
    def update_paper(self, paper: Paper) -> bool:
        """
        Update an existing paper.
        
        Args:
            paper: Paper object with updated information (must have id set)
            
        Returns:
            True if successful, False otherwise
        """
        if not paper.id:
            return False
        
        cursor = self.connection.cursor()
        now = datetime.now().isoformat()
        
        cursor.execute("""
            UPDATE papers SET
                title = ?, authors = ?, year = ?, resource_type = ?, doi = ?,
                url = ?, arxiv_id = ?, journal = ?, conference = ?, publisher = ?,
                volume = ?, issue = ?, pages = ?, accessibility_status = ?,
                last_checked = ?, download_url = ?, requires_authentication = ?,
                authentication_service = ?, local_file_path = ?, abstract = ?,
                keywords = ?, notes = ?, updated_at = ?
            WHERE id = ?
        """, (
            paper.title,
            json.dumps(paper.authors),
            paper.year,
            paper.resource_type.value if paper.resource_type else None,
            paper.doi,
            paper.url,
            paper.arxiv_id,
            paper.journal,
            paper.conference,
            paper.publisher,
            paper.volume,
            paper.issue,
            paper.pages,
            paper.accessibility_status.value if paper.accessibility_status else None,
            paper.last_checked.isoformat() if paper.last_checked else None,
            paper.download_url,
            1 if paper.requires_authentication else 0,
            paper.authentication_service,
            paper.local_file_path,
            paper.abstract,
            json.dumps(paper.keywords),
            paper.notes,
            now,
            paper.id
        ))
        
        self.connection.commit()
        return cursor.rowcount > 0
    
    def delete_paper(self, paper_id: int) -> bool:
        """
        Delete a paper from the database.
        
        Args:
            paper_id: ID of the paper to delete
            
        Returns:
            True if successful, False otherwise
        """
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM papers WHERE id = ?", (paper_id,))
        self.connection.commit()
        return cursor.rowcount > 0
    
    def search_papers(
        self,
        query: Optional[str] = None,
        status: Optional[AccessibilityStatus] = None,
        resource_type: Optional[ResourceType] = None,
        year: Optional[int] = None,
        limit: int = 100
    ) -> List[Paper]:
        """
        Search papers with various filters.
        
        Args:
            query: Search query for title, authors, or abstract
            status: Filter by accessibility status
            resource_type: Filter by resource type
            year: Filter by publication year
            limit: Maximum number of results
            
        Returns:
            List of matching papers
        """
        cursor = self.connection.cursor()
        
        sql = "SELECT * FROM papers WHERE 1=1"
        params = []
        
        if query:
            sql += " AND (title LIKE ? OR authors LIKE ? OR abstract LIKE ?)"
            search_term = f"%{query}%"
            params.extend([search_term, search_term, search_term])
        
        if status:
            sql += " AND accessibility_status = ?"
            params.append(status.value)
        
        if resource_type:
            sql += " AND resource_type = ?"
            params.append(resource_type.value)
        
        if year:
            sql += " AND year = ?"
            params.append(year)
        
        sql += f" ORDER BY created_at DESC LIMIT {limit}"
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        
        return [self._row_to_paper(row) for row in rows]
    
    def get_all_papers(self, limit: int = 1000) -> List[Paper]:
        """
        Get all papers from the database.
        
        Args:
            limit: Maximum number of papers to return
            
        Returns:
            List of all papers
        """
        cursor = self.connection.cursor()
        cursor.execute(f"SELECT * FROM papers ORDER BY created_at DESC LIMIT {limit}")
        rows = cursor.fetchall()
        return [self._row_to_paper(row) for row in rows]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get database statistics.
        
        Returns:
            Dictionary with statistics
        """
        cursor = self.connection.cursor()
        
        # Total count
        cursor.execute("SELECT COUNT(*) FROM papers")
        total = cursor.fetchone()[0]
        
        # Count by status
        cursor.execute("""
            SELECT accessibility_status, COUNT(*) 
            FROM papers 
            GROUP BY accessibility_status
        """)
        status_counts = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Count by resource type
        cursor.execute("""
            SELECT resource_type, COUNT(*) 
            FROM papers 
            GROUP BY resource_type
        """)
        type_counts = {row[0]: row[1] for row in cursor.fetchall()}
        
        return {
            "total_papers": total,
            "by_status": status_counts,
            "by_type": type_counts
        }
    
    def _row_to_paper(self, row: sqlite3.Row) -> Paper:
        """Convert database row to Paper object"""
        return Paper(
            id=row["id"],
            title=row["title"],
            authors=json.loads(row["authors"]) if row["authors"] else [],
            year=row["year"],
            resource_type=ResourceType(row["resource_type"]) if row["resource_type"] else ResourceType.PAPER,
            doi=row["doi"],
            url=row["url"],
            arxiv_id=row["arxiv_id"],
            journal=row["journal"],
            conference=row["conference"],
            publisher=row["publisher"],
            volume=row["volume"],
            issue=row["issue"],
            pages=row["pages"],
            accessibility_status=AccessibilityStatus(row["accessibility_status"]) if row["accessibility_status"] else AccessibilityStatus.UNKNOWN,
            last_checked=datetime.fromisoformat(row["last_checked"]) if row["last_checked"] else None,
            download_url=row["download_url"],
            requires_authentication=bool(row["requires_authentication"]),
            authentication_service=row["authentication_service"],
            local_file_path=row["local_file_path"],
            abstract=row["abstract"],
            keywords=json.loads(row["keywords"]) if row["keywords"] else [],
            notes=row["notes"],
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None,
        )
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
