from nicegui import ui

from loja.campos_formulario import (
    input_data,
    input_email,
    input_numero,
    input_texto,
    textarea_texto,
)
from loja.repositorio import (
    CAMBIOS,
    COMBUSTIVEIS,
    ESTADO_PNEUS,
    config_como_dict,
    salvar_avaliacao,
)
from loja.tenant_ctx import get_tenant_slug, ligar_tenant


def montar_formulario_avaliacao() -> None:
    loja = config_como_dict()
    slug = get_tenant_slug()

    ui.html(
        f'<div class="avaliacao-topo">'
        f"<h1>FORMULÁRIO DE AVALIAÇÃO</h1>"
        f"<h2>{loja['nome'].upper()}</h2></div>"
    )

    with ui.element("form").classes("form-avaliacao form-site"):
        ui.html('<h3 class="form-secao">DADOS DO VEÍCULO</h3>')
        with ui.element("div").classes("form-grid"):
            marca = input_texto("Marca", placeholder="Ex. Jeep")
            modelo = input_texto("Modelo", placeholder="Ex. ASX")
            ano = input_numero("Ano", placeholder="Ano")
            renavam = input_numero("Renavam", placeholder="Renavam")
            km = input_numero("Quilometragem", placeholder="Km")
            cor = input_texto("Cor (Manual do veículo)", placeholder="Ex. Azul")

        with ui.element("div").classes("form-grid-tres"):
            ui.label("Revisões na autorizada").classes("form-label")
            revisao = ui.radio(["Sim", "Não"], value="Não").props("inline dense")
            ui.label("Sinistro").classes("form-label")
            sinistro = ui.radio(["Sim", "Não"], value="Não").props("inline dense")

        with ui.element("div").classes("form-grid"):
            combustivel = ui.select(
                COMBUSTIVEIS, label="Combustível", with_input=False,
            ).props("outlined dense")
            cambio = ui.select(
                CAMBIOS, label="Câmbio", with_input=False,
            ).props("outlined dense")
            estado_pneus = ui.select(
                ESTADO_PNEUS, label="Estado dos Pneus", with_input=False,
            ).props("outlined dense")
            acessorio = input_texto("Acessório extra", placeholder="Ex. Airbag Duplo")

        ui.html('<h3 class="form-secao">DADOS PESSOAIS</h3>')
        nome = input_texto("Nome", placeholder="Seu Nome", classes="form-full")
        with ui.element("div").classes("form-grid"):
            ddi = input_numero("DDI", value="55", placeholder="55")
            telefone = input_numero("Telefone", placeholder="Telefone")
            email = input_email("E-mail", placeholder="Seu e-mail")
            nascimento = input_data("Data de nascimento", placeholder="DD/MM/AAAA")
        endereco = input_texto("Endereço", placeholder="Seu endereço", classes="form-full")
        with ui.element("div").classes("form-grid"):
            profissao = input_texto("Profissão", placeholder="Sua profissão")
            cpf = input_numero("CPF", placeholder="Seu CPF")
            conheceu = input_texto(
                f"Como conheceu a {loja['nome']}?",
                placeholder="Ex. Internet",
            )

        ui.label("Qual a sua intenção?").classes("form-label mt")
        intencao = ui.radio(
            {
                "vender": "Deseja somente vender?",
                "vender_comprar": "Deseja vender e comprar?",
            },
            value="vender_comprar",
        ).props("inline dense")

        interesse = input_texto(
            "Qual veículo lhe interessou em nosso estoque?",
            placeholder="Ex. Porsche Boxster",
            classes="form-full",
        )

        def enviar() -> None:
            if not nome.value or not telefone.value:
                ui.notify("Preencha nome e telefone.", type="warning")
                return
            if not marca.value or not modelo.value:
                ui.notify("Informe marca e modelo do veículo.", type="warning")
                return
            if slug:
                ligar_tenant(slug)
            salvar_avaliacao({
                "marca": marca.value.strip(),
                "modelo": modelo.value.strip(),
                "ano": ano.value or "",
                "renavam": renavam.value or "",
                "km": km.value or "",
                "revisao_autorizada": revisao.value == "Sim",
                "cor": cor.value or "",
                "sinistro": sinistro.value == "Sim",
                "combustivel": combustivel.value or "",
                "cambio": cambio.value or "",
                "estado_pneus": estado_pneus.value or "",
                "acessorio_extra": acessorio.value or "",
                "nome": nome.value.strip(),
                "ddi": ddi.value or "55",
                "telefone": telefone.value.strip(),
                "email": email.value or "",
                "data_nascimento": nascimento.value or "",
                "endereco": endereco.value or "",
                "profissao": profissao.value or "",
                "cpf": cpf.value or "",
                "como_conheceu": conheceu.value or "",
                "intencao": intencao.value or "vender_comprar",
                "veiculo_interesse": interesse.value or "",
                "status": "novo",
            })
            ui.notify(
                "Avaliação enviada! Entraremos em contato em breve.",
                type="positive",
            )

        ui.button(
            "Enviar avaliação", on_click=enviar,
        ).classes("btn btn-preto btn-enviar-avaliacao").props("unelevated no-caps")
