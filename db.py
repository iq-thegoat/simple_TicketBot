from sqlalchemy import create_engine, ForeignKey, Column, String, Integer, DateTime
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime


global base
Base = declarative_base()



class DbStruct:
    class Live_Tickets(Base):
        __tablename__ = "live_tickets"
        id = Column("id",Integer,primary_key=True,autoincrement=True)
        channel_id = Column("channel_id",Integer)
        ticket_creator = Column("ticket_creator",Integer)
        creation_date  = Column("creation_date", DateTime, default=datetime.datetime.utcnow)
        claimed_by     = Column("claimed_by",Integer,default=None)
    
        def __init__(self,ticket_creator:int,channel_id:int,claimed_by:int =None):
            self.ticket_creator = ticket_creator
            self.claimed_by = claimed_by
            self.channel_id = channel_id
    
    class Tickets_Archive(Base):
        __tablename__ = "Tickets_Archive"
        id = Column("id",Integer,primary_key=True,autoincrement=True)
        ticket_creator = Column("ticket_creator",Integer)
        creation_date  = Column("creation_date", DateTime, default=datetime.datetime.utcnow)
        claimed_by     = Column("claimed_by",Integer,default=None)
        close_date  = Column("close_date", DateTime, default=datetime.datetime.utcnow)

        def __init__(self,ticket_creator:int,creation_date:datetime.datetime,claimed_by:int =None):
            self.ticket_creator = ticket_creator
            self.claimed_by = claimed_by
            self.creation_date = creation_date






class BotDb:
    def __init__(self) -> None:
        engine = create_engine("sqlite:///database.db")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        self.session = Session()
