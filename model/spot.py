from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, Index

from util.database import Base


class Spot(Base):
    """
    景點模型 - 代表在資料庫中的 public.spot 表
    """
    __tablename__ = "spot"
    __table_args__ = (
        Index("idx_spot_location", "location", postgresql_using="gist"),
        Index("idx_spot_popularity", "popularity", postgresql_using=None),
        {"schema": "public"}
    )

    # 主鍵
    spot_id = Column(Integer, primary_key=True, autoincrement=True)

    # 基本信息
    name = Column(String(255), nullable=False, comment="景點名稱")
    description = Column(Text, nullable=True, comment="景點描述")

    # 地理位置信息
    country = Column(String(12), nullable=True, comment="國家")
    city = Column(String(12), nullable=True, comment="城市")
    district = Column(String(12), nullable=True, comment="區域")
    street_address = Column(String(255), nullable=True, comment="街道地址")
    location = Column(
        Geometry(geometry_type="Point", srid=4326),
        nullable=True,
        comment="地理位置座標 (WGS84)"
    )

    # 評分和人氣
    rating = Column(
        Float,
        nullable=True,
        comment="評分 (0-5)"
    )
    popularity = Column(
        Integer,
        default=0,
        nullable=False,
        comment="人氣度"
    )

    # 狀態字段
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="是否活躍"
    )

    # 時間戳
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        comment="建立時間"
    )
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        comment="更新時間"
    )

    category = Column(
        String(36),
        nullable=True,
        comment="景點類別"
    )


    def __repr__(self):
        return f"<Spot(spot_id={self.spot_id}, name='{self.name}', city='{self.city}')>"

