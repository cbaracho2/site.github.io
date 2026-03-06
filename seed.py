"""Seed the database with a default admin user and sample data."""

from app import create_app
from models import db, Empresa, User, Empreendimento, Bloco, Unidade, PlanoPadrao, RegrasEmpreendimento


def seed():
    app = create_app()
    with app.app_context():
        db.create_all()

        # Check if already seeded
        if User.query.filter_by(email='admin@admin.com').first():
            print('Database already seeded.')
            return

        # Create default empresa
        empresa = Empresa(nome='Construtora Modelo', cnpj='00.000.000/0001-00')
        db.session.add(empresa)
        db.session.flush()

        # Create admin user
        admin = User(
            nome='Administrador',
            email='admin@admin.com',
            role='adm',
            empresa_id=empresa.id,
            ativo=True
        )
        admin.set_password('admin123')
        db.session.add(admin)

        # Create sample empreendimento
        emp = Empreendimento(
            nome='Residencial Parque das Flores',
            endereco='Rua das Flores, 100 - Centro',
            empresa_id=empresa.id,
            taxa_desconto_mensal=0.01
        )
        db.session.add(emp)
        db.session.flush()

        # Create plano padrao
        plano = PlanoPadrao(
            empreendimento_id=emp.id,
            sinal_qtd=3,
            sinal_pct=10.0,
            mensal_qtd=36,
            mensal_pct=20.0,
            intermediaria_qtd=4,
            intermediaria_pct=10.0,
            intermediaria_periodicidade='S',
            chave_pct=10.0,
            financiamento_pct=50.0
        )
        db.session.add(plano)

        # Create regras
        regras = RegrasEmpreendimento(
            empreendimento_id=emp.id,
            pct_min_sinal=5.0,
            pct_min_mensal=5.0,
            qtd_max_mensal=48,
            pct_min_financiamento=0.0,
            pct_max_financiamento=80.0,
            valor_max_chave=0.0,
            qtd_max_bimestrais=0,
            qtd_max_trimestrais=0,
            qtd_max_semestrais=4,
            qtd_max_anuais=2
        )
        db.session.add(regras)

        # Create blocos and unidades
        for bloco_nome in ['Bloco A', 'Bloco B']:
            bloco = Bloco(nome=bloco_nome, empreendimento_id=emp.id)
            db.session.add(bloco)
            db.session.flush()

            for i in range(1, 5):
                for andar in range(1, 4):
                    num = f'{andar}0{i}'
                    unidade = Unidade(
                        numero=num,
                        bloco_id=bloco.id,
                        descricao=f'Apto {num} - 2 quartos',
                        area_coberta=55.0 + (i * 5),
                        area_descoberta=8.0 + (i * 2),
                        preco_m2=6500.00,
                        coef_area_descoberta=0.5,
                        status='disponivel'
                    )
                    db.session.add(unidade)

        db.session.commit()
        print('Database seeded successfully!')
        print('Admin login: admin@admin.com / admin123')


if __name__ == '__main__':
    seed()
