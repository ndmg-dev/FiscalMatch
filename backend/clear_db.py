from app.core.database import SessionLocal
from app.models.company import Empresa
from app.models.sped import ArquivoSped, DocumentoSped
from app.models.xml import DocumentoXML
from app.models.reconciliation import Conciliacao

def clear():
    db = SessionLocal()
    try:
        db.query(Conciliacao).delete()
        db.query(DocumentoXML).delete()
        db.query(DocumentoSped).delete()
        db.query(ArquivoSped).delete()
        db.commit()
        print("✅ Banco limpo com sucesso! (A sua Empresa cadastrada foi mantida para facilitar)")
    except Exception as e:
        db.rollback()
        print(f"❌ Erro ao limpar o banco: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    clear()
