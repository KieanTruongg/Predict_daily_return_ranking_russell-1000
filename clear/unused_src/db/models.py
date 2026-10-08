"""Database models using SQLAlchemy ORM (Phase 6).
Stores predictions, model metadata, and backtest results in SQLite/PostgreSQL.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class PredictionRecord(Base):
    """Stores daily predicted stock rankings and positions."""
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String(20), nullable=False, index=True)
    ticker = Column(String(20), nullable=False, index=True)
    predicted_rank = Column(Float, nullable=False)
    target_weight = Column(Float, nullable=False)
    position_type = Column(String(10), nullable=False)  # 'LONG', 'SHORT', 'NEUTRAL'
    model_version = Column(String(50), default="meta_v1")
    created_at = Column(DateTime, default=datetime.utcnow)


class BacktestRun(Base):
    """Stores historical backtest run metrics."""
    __tablename__ = "backtest_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_name = Column(String(100), nullable=False)
    start_date = Column(String(20))
    end_date = Column(String(20))
    annualized_return = Column(Float)
    sharpe_ratio = Column(Float)
    max_drawdown = Column(Float)
    win_rate = Column(Float)
    turnover = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db(db_url: str = "sqlite:///data/quant_system.db"):
    engine = create_engine(db_url, echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return engine, Session
