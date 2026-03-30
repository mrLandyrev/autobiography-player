
from sqlalchemy import select, create_engine, Table, Column, String, ForeignKey, Boolean, Integer, JSON
from sqlalchemy.orm import Session, DeclarativeBase, Mapped, mapped_column, relationship
from typing import List

engine = create_engine('sqlite:///cache/tracks.db', echo=False)

class Base(DeclarativeBase):
    pass


tracks_to_authors_table = Table(
    "tracks_to_authors_table",
    Base.metadata,
    Column("left_id", ForeignKey("tracks.id"), primary_key=True),
    Column("right_id", ForeignKey("authors.id"), primary_key=True),
)


class Track(Base):
    __tablename__ = "tracks"
    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    authors: Mapped[List["Author"]] = relationship(
        secondary=tracks_to_authors_table,
        back_populates="tracks",
    )
    duration: Mapped[int] = mapped_column(Integer)
    isDownloaded: Mapped[bool] = mapped_column(Boolean)
    isDownloading: Mapped[bool] = mapped_column(Boolean)


class Author(Base):
    __tablename__ = "authors"
    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    tracks: Mapped[List["Track"]] = relationship(
        secondary=tracks_to_authors_table,
        back_populates="authors"
    )

class Listen(Base):
    __tablename__ = "listens"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    started_at: Mapped[int] = mapped_column(Integer)
    track_id: Mapped[str] = mapped_column(String)

class Playlist(Base):
    __tablename__ = "playlists"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    position: Mapped[int] = mapped_column(Integer)
    time: Mapped[int] = mapped_column(Integer)
    tracks: Mapped[List[str]] = mapped_column(JSON)

Base.metadata.create_all(engine)