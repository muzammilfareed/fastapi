from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from functools import lru_cache
from typing import Optional
from typing import Dict

app = FastAPI()

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    posts = relationship("Post", back_populates="author")

class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True, index=True)
    text = Column(String)
    author_id = Column(Integer, ForeignKey("users.id"))
    author = relationship("User", back_populates="posts")

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class UserCreate(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class PostCreate(BaseModel):
    text: str

def generate_token():
    return "fake_token"

def authenticate_user(email: str, password: str):
    return True

def get_current_user(token: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == token).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user



@app.post("/signup", response_model=Token)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    db_user = User(email=user.email, password=user.password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"access_token": db_user.email, "token_type": "bearer"}

@app.post("/login", response_model=Token)
def login(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    password_check = authenticate_user(db_user.password, user.password)
    print(password_check)

    if not db_user or not authenticate_user(db_user.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"access_token": db_user.email, "token_type": "bearer"}

@app.post("/addPost", response_model=str)
def add_post(post: PostCreate, token: str = Depends(get_current_user), db: Session = Depends(get_db)):

    print(token.id)
    print(post.text)
    post_db = Post(text=post.text, author_id=token.id)
    db.add(post_db)
    db.commit()
    db.refresh(post_db)
    return str(post_db.id)

@app.get("/getPosts", response_model=Dict[str, str])
@lru_cache(maxsize=128)  # Response caching
def get_posts(token: Optional[str] = None, db: Session = Depends(get_db)):
    if token:
        user = db.query(User).filter(User.token == token).first()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        posts = {str(post.id): post.text for post in user.posts}
        return posts
    else:
        all_posts = db.query(Post).all()
        posts = {str(post.id): post.text for post in all_posts}
        return posts

@app.delete("/deletePost", response_model=Dict[str, str])
def delete_post(post_id: int, token: str = Depends(get_current_user), db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id, Post.author_id == token.id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    db.delete(post)
    db.commit()
    return {"message": "Post deleted successfully"}
