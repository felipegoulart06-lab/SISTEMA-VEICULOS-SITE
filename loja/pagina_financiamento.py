from nicegui import ui

from loja.campos_formulario import (
    input_data,
    input_email,
    input_numero,
    input_texto,
    textarea_texto,
)
from loja.crm_repo import salvar_financiamento_site
from loja.repositorio import config_como_dict
from loja.tenant_ctx import get_tenant_slug, ligar_tenant

UFS = [
    "", "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP",
    "SE", "TO",
]
ESTADOS_CIVIS = ["", "Solteiro(a)", "Casado(a)", "Divorciado(a)", "Viúvo(a)", "União estável"]
SEXOS = ["", "Masculino", "Feminino", "Prefiro não informar"]


def montar_formulario_financiamento(
    marca: str = "",
    modelo: str = "",
    ano: str = "",
    cor: str = "",
    valor: float = 0,
    veiculo_id: int = 0,
) -> None:
    slug = get_tenant_slug()
    loja = config_como_dict()
    ano_str = str(ano or "")
    ano_fab = ano_str[:4] if len(ano_str) >= 4 else ano_str
    ano_mod = ano_str[:4] if len(ano_str) >= 4 else ano_str

    ui.html(
        f'<div class="fin-topo">'
        f"<h1>APROVE SEU FINANCIAMENTO ON-LINE</h1>"
        f"<p>Preencha o formulário abaixo para aprovar seu financiamento.</p>"
        f"</div>"
    )

    ui.html(
        '<section class="fin-docs">'
        "<h2 class=\"form-secao\">Documentações</h2>"
        '<div class="fin-docs-grid">'
        '<div class="fin-doc-item">'
        '<span class="material-icons">badge</span>'
        "<div><strong>CNH</strong>"
        "<span>(Carteira Nacional de Habilitação)</span></div></div>"
        '<div class="fin-doc-item">'
        '<span class="material-icons">home</span>'
        "<div><strong>Comprovante de Residência</strong>"
        "<span>(Conta de Água, Luz, Telefone, Cartão de Crédito)</span></div></div>"
        '<div class="fin-doc-item">'
        '<span class="material-icons">receipt_long</span>'
        "<div><strong>Comprovante de Renda</strong>"
        "<span>(Contra-Cheque, Extrato Bancário últimos 90 dias, Imposto de Renda)</span>"
        "</div></div></div></section>"
    )

    with ui.element("form").classes("form-avaliacao form-financiamento form-site"):
        ui.html('<h3 class="form-secao">DADOS DO VEÍCULO</h3>')
        with ui.element("div").classes("form-grid"):
            v_marca = input_texto("Marca", value=marca, placeholder="Ex. Volkswagen")
            v_modelo = input_texto("Modelo", value=modelo, placeholder="Ex. Golf")
        with ui.element("div").classes("form-grid form-grid-veiculo-ano"):
            with ui.element("div").classes("form-ano-wrap"):
                ui.html('<span class="form-ano-label">Ano/Modelo</span>')
                with ui.element("div").classes("form-ano-par"):
                    v_ano_fab = input_numero("Fab.", value=ano_fab, placeholder="2020")
                    ui.html('<span class="form-ano-barra">/</span>')
                    v_ano_mod = input_numero("Mod.", value=ano_mod, placeholder="2020")
            v_cor = input_texto("Cor", value=cor, placeholder="Ex. Preto")
        with ui.element("div").classes("form-grid form-grid-tres-col"):
            v_valor = ui.number(
                "Valor (R$)", value=float(valor or 0), format="%.2f",
                placeholder="Valor do veículo",
            ).props("outlined dense")
            v_entrada = ui.number(
                "Valor de entrada (R$)", value=0, format="%.2f",
                placeholder="Valor da entrada",
            ).props("outlined dense")
            v_prest = ui.number(
                "Qtd Prestações", value=48, format="%.0f",
                placeholder="Prestações",
            ).props("outlined dense")

        ui.html('<h3 class="form-secao">DADOS PESSOAIS</h3>')
        p_nome = input_texto("Nome", placeholder="Seu nome", classes="form-full")
        with ui.element("div").classes("form-grid"):
            p_cpf = input_numero("CPF", placeholder="Seu CPF")
            p_rg = input_numero("RG", placeholder="Seu RG")
            p_nasc = input_data("Data de Nascimento", placeholder="__/__/____")
            p_nat = input_texto("Naturalidade", placeholder="Naturalidade")
        with ui.element("div").classes("form-grid"):
            p_mae = input_texto("Nome da Mãe", placeholder="Nome da Mãe")
            p_pai = input_texto("Nome do Pai", placeholder="Nome do Pai")
            p_civil = ui.select(
                ESTADOS_CIVIS, label="Estado Civil", with_input=False,
            ).props("outlined dense")
            p_sexo = ui.select(
                SEXOS, label="Sexo", with_input=False,
            ).props("outlined dense")
        p_email = input_email("Email", placeholder="Seu email", classes="form-full")
        with ui.element("div").classes("form-grid"):
            tel_ddd, tel_num = _campo_telefone("Telefone", "Telefone fixo")
            cel_ddd, cel_num = _campo_telefone("Celular", "Telefone celular")
        with ui.element("div").classes("form-grid"):
            p_end = input_texto(
                "Endereço", placeholder="Seu endereço", classes="form-span-2",
            )
            p_num = input_numero("Número", placeholder="Número")
        with ui.element("div").classes("form-grid"):
            p_compl = input_texto("Complemento", placeholder="Complemento")
            p_cep = input_numero("CEP", placeholder="CEP")
            p_bairro = input_texto("Bairro", placeholder="Bairro")
        with ui.element("div").classes("form-grid"):
            p_cidade = input_texto("Cidade", placeholder="Cidade")
            p_uf = ui.select(
                {u: u or "-- Selecione --" for u in UFS},
                label="Estado", with_input=False,
            ).props("outlined dense")
            p_tempo_res = input_texto(
                "Tempo de Residência", placeholder="Tempo de residência",
            )

        ui.html('<h3 class="form-secao">DADOS PROFISSIONAIS</h3>')
        with ui.element("div").classes("form-grid"):
            pr_empresa = input_texto(
                "Empresa onde trabalha", placeholder="Empresa onde trabalha",
            )
            pr_cnpj = input_numero("CNPJ", placeholder="CNPJ")
            pr_cargo = input_texto("Cargo/Função", placeholder="Cargo/Função")
            pr_renda = ui.number(
                "Renda (R$)", value=0, format="%.2f", placeholder="Renda atual",
            ).props("outlined dense")
        with ui.element("div").classes("form-grid"):
            pr_end = input_texto(
                "Endereço", placeholder="Endereço da empresa", classes="form-span-2",
            )
            pr_num = input_numero("Número", placeholder="Número")
        with ui.element("div").classes("form-grid"):
            pr_compl = input_texto("Complemento", placeholder="Complemento")
            pr_cep = input_numero("CEP", placeholder="CEP")
            pr_bairro = input_texto("Bairro", placeholder="Bairro")
        with ui.element("div").classes("form-grid"):
            pr_cidade = input_texto("Cidade", placeholder="Cidade")
            pr_uf = ui.select(
                {u: u or "-- Selecione --" for u in UFS},
                label="Estado", with_input=False,
            ).props("outlined dense")
            pr_tempo = input_texto(
                "Tempo neste emprego", placeholder="Tempo neste emprego",
            )
        pr_tel_ddd, pr_tel_num = _campo_telefone(
            "Telefone", "Telefone empresa", full_width=True,
        )

        ui.html('<h3 class="form-secao">REFERÊNCIA BANCÁRIA</h3>')
        with ui.element("div").classes("form-grid"):
            b_banco = input_texto("Banco", placeholder="Nome do banco")
            b_ag = input_numero("Agência", placeholder="Número da agência")
            b_conta = input_numero("Conta", placeholder="Número da conta")
            b_tempo = input_texto("Tempo de conta", placeholder="Tempo de conta")

        ui.html('<h3 class="form-secao">REFERÊNCIA PESSOAL</h3>')
        with ui.element("div").classes("form-grid"):
            r1_nome = input_texto("Nome", placeholder="Nome")
            r1_ddd, r1_tel = _campo_telefone_inline("Telefone")
        with ui.element("div").classes("form-grid"):
            r2_nome = input_texto("Nome", placeholder="Nome")
            r2_ddd, r2_tel = _campo_telefone_inline("Telefone")

        ui.html('<h3 class="form-secao">INFORMAÇÕES ADICIONAIS</h3>')
        info_extra = textarea_texto(
            "Informações adicionais", placeholder="Informações adicionais",
            classes="form-full",
        )

        ui.html(
            '<p class="fin-aviso">*Consulte condições para cartão de crédito</p>'
        )

        def enviar() -> None:
            if not p_nome.value or not p_cpf.value:
                ui.notify("Preencha nome e CPF.", type="warning")
                return
            if not cel_ddd.value or not cel_num.value:
                ui.notify("Preencha o celular com DDD.", type="warning")
                return
            if not v_marca.value or not v_modelo.value:
                ui.notify("Informe marca e modelo do veículo.", type="warning")
                return

            celular = f"{cel_ddd.value}{cel_num.value}".strip()
            telefone = (
                f"{tel_ddd.value}{tel_num.value}".strip()
                if tel_ddd.value and tel_num.value else ""
            )

            payload = {
                "nome": p_nome.value.strip(),
                "cpf": p_cpf.value or "",
                "rg": p_rg.value or "",
                "data_nascimento": p_nasc.value or "",
                "nome_mae": p_mae.value or "",
                "nome_pai": p_pai.value or "",
                "naturalidade": p_nat.value or "",
                "estado_civil": p_civil.value or "",
                "sexo": p_sexo.value or "",
                "email": p_email.value or "",
                "telefone": telefone,
                "celular": celular,
                "endereco": p_end.value or "",
                "numero": p_num.value or "",
                "complemento": p_compl.value or "",
                "cep": p_cep.value or "",
                "bairro": p_bairro.value or "",
                "cidade": p_cidade.value or "",
                "estado": p_uf.value or "",
                "tempo_residencia": p_tempo_res.value or "",
                "veiculo_marca": v_marca.value.strip(),
                "veiculo_modelo": v_modelo.value.strip(),
                "veiculo_ano_fab": v_ano_fab.value or "",
                "veiculo_ano_mod": v_ano_mod.value or "",
                "veiculo_cor": v_cor.value or "",
                "valor_veiculo": float(v_valor.value or 0),
                "valor_entrada": float(v_entrada.value or 0),
                "qtd_prestacoes": int(v_prest.value or 0),
                "veiculo_id": veiculo_id or None,
                "empresa": pr_empresa.value or "",
                "empresa_cnpj": pr_cnpj.value or "",
                "cargo": pr_cargo.value or "",
                "renda": float(pr_renda.value or 0),
                "empresa_endereco": pr_end.value or "",
                "empresa_numero": pr_num.value or "",
                "empresa_complemento": pr_compl.value or "",
                "empresa_cep": pr_cep.value or "",
                "empresa_bairro": pr_bairro.value or "",
                "empresa_cidade": pr_cidade.value or "",
                "empresa_estado": pr_uf.value or "",
                "empresa_telefone": (
                    f"{pr_tel_ddd.value}{pr_tel_num.value}".strip()
                    if pr_tel_ddd.value and pr_tel_num.value else ""
                ),
                "tempo_emprego": pr_tempo.value or "",
                "banco": b_banco.value or "",
                "agencia": b_ag.value or "",
                "conta": b_conta.value or "",
                "tempo_conta": b_tempo.value or "",
                "ref1_nome": r1_nome.value or "",
                "ref1_telefone": (
                    f"{r1_ddd.value}{r1_tel.value}".strip()
                    if r1_ddd.value and r1_tel.value else ""
                ),
                "ref2_nome": r2_nome.value or "",
                "ref2_telefone": (
                    f"{r2_ddd.value}{r2_tel.value}".strip()
                    if r2_ddd.value and r2_tel.value else ""
                ),
                "informacoes_adicionais": info_extra.value or "",
                "loja": loja.get("nome", ""),
            }
            if slug:
                ligar_tenant(slug)
            salvar_financiamento_site(payload)
            ui.notify(
                "Financiamento enviado! Nossa equipe analisará e entrará em contato.",
                type="positive",
            )
            ui.run_javascript("window.scrollTo({top: 0, behavior: 'smooth'})")

        ui.button(
            "Enviar financiamento",
            on_click=enviar,
        ).classes("btn btn-preto btn-enviar-avaliacao").props("unelevated no-caps")


def _campo_telefone(rotulo: str, placeholder: str, full_width: bool = False):
    cls = "form-grid-tel form-full" if full_width else "form-grid-tel"
    with ui.element("div").classes(cls):
        ddd = input_numero("DDD", placeholder="DDD").classes("fin-ddd")
        num = input_numero(rotulo, placeholder=placeholder)
    return ddd, num


def _campo_telefone_inline(rotulo: str):
    with ui.element("div").classes("form-grid-tel"):
        ddd = input_numero("DDD", placeholder="DDD").classes("fin-ddd")
        num = input_numero(rotulo, placeholder="Telefone")
    return ddd, num
