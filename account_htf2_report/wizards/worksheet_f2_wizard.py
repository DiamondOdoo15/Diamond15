# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import *
from odoo.exceptions import UserError
import base64

class WorksheetF2Wizard(models.TransientModel):
	_name = 'worksheet.f2.wizard'

	name = fields.Char()
	company_id = fields.Many2one('res.company',string=u'Compañia',required=True, default=lambda self: self.env.company,readonly=True)
	fiscal_year_id = fields.Many2one('account.fiscal.year',string='Ejercicio',required=True)
	period_id = fields.Many2one('account.period',string='Periodo',required=True)
	type_show =  fields.Selection([('pantalla','Pantalla'),('excel','Excel')],default='excel',string=u'Mostrar en', required=True)
	level = fields.Selection([('balance','Balance'),('register','Registro')],default='balance',string='Nivel',required=True)

	@api.onchange('company_id')
	def get_fiscal_year(self):
		if self.company_id:
			today = fields.Date.context_today(self)
			fiscal_year = self.env['account.fiscal.year'].search([('name','=',str(today.year))],limit=1)
			if fiscal_year:
				self.fiscal_year_id = fiscal_year.id

	def _get_f2_register_sql(self):
		sql = """
			select 
			'{date_from}'::date as date_from,
			'{date_to}'::date as date_to, T.* FROM(
			(select
			left(a2.code,2) as mayor,
			a2.code as cuenta,
			a2.name as nomenclatura,
			a1.si_debe,
			a1.si_haber,
			a1.debe,
			a1.haber,
			case when a1.debe > a1.haber then a1.debe-a1.haber else  0 end as saldo_deudor,
			case when a1.haber> a1.debe then a1.haber-a1.debe else 0 end as saldo_acreedor,
			case when a2.clasification_sheet='0' and a1.debe>a1.haber then a1.debe-a1.haber else 0 end as activo,
			case when a2.clasification_sheet='0' and a1.haber>a1.debe then a1.haber-a1.debe else 0 end as pasivo,
			case when (a2.clasification_sheet='1' or a2.clasification_sheet='3') and a1.debe>a1.haber then a1.debe-a1.haber else 0 end as perdinat,
			case when (a2.clasification_sheet='1' or a2.clasification_sheet='3') and a1.haber>a1.debe then a1.haber-a1.debe else 0 end as ganannat,
			case when (a2.clasification_sheet='2' or a2.clasification_sheet='3') and a1.debe>a1.haber then a1.debe-a1.haber else 0 end as perdifun,
			case when (a2.clasification_sheet='2' or a2.clasification_sheet='3') and a1.haber>a1.debe then a1.haber-a1.debe else 0 end as gananfun
			from get_sumas_mayor_f2('{date_from}','{date_to}',{company_id}) a1
			left join account_account a2 on a2.id=a1.account_id
			order by a2.code)
			UNION ALL
			(SELECT 
			null::character varying as mayor,
			null::character varying as cuenta,
			'SUMAS'::character varying as nomenclatura,
			sum(a1.si_debe) as si_debe,
			sum(a1.si_haber) as si_haber,
			sum(a1.debe) as debe,
			sum(a1.haber) as haber,
			sum(case when a1.debe > a1.haber then a1.debe-a1.haber else  0 end) as saldo_deudor,
			sum(case when a1.haber> a1.debe then a1.haber-a1.debe else 0 end) as saldo_acreedor,
			sum(case when a2.clasification_sheet='0' and a1.debe>a1.haber then a1.debe-a1.haber else 0 end) as activo,
			sum(case when a2.clasification_sheet='0' and a1.haber>a1.debe then a1.haber-a1.debe else 0 end) as pasivo,
			sum(case when (a2.clasification_sheet='1' or a2.clasification_sheet='3') and a1.debe>a1.haber then a1.debe-a1.haber else 0 end) as perdinat,
			sum(case when (a2.clasification_sheet='1' or a2.clasification_sheet='3') and a1.haber>a1.debe then a1.haber-a1.debe else 0 end) as ganannat,
			sum(case when (a2.clasification_sheet='2' or a2.clasification_sheet='3') and a1.debe>a1.haber then a1.debe-a1.haber else 0 end) as perdifun,
			sum(case when (a2.clasification_sheet='2' or a2.clasification_sheet='3') and a1.haber>a1.debe then a1.haber-a1.debe else 0 end) as gananfun
			from get_sumas_mayor_f2('{date_from}','{date_to}',{company_id}) a1
			left join account_account a2 on a2.id=a1.account_id)
			UNION ALL
			(SELECT 
			null::character varying as mayor,
			null::character varying as cuenta,
			'UTILIDAD O PERDIDA'::character varying as nomenclatura,
			case
				when sum(a1.si_debe) < sum(a1.si_haber)
				then sum(a1.si_haber) - sum(a1.si_debe)
				else 0
			end as si_debe,
			case
				when sum(a1.si_debe) > sum(a1.si_haber)
				then sum(a1.si_debe) - sum(a1.si_haber) 
				else 0
			end as si_haber,
			case
				when sum(a1.debe) < sum(a1.haber)
				then sum(a1.haber) - sum(a1.debe)
				else 0
			end as debe,
			case
				when sum(a1.debe) > sum(a1.haber)
				then sum(a1.debe) - sum(a1.haber) 
				else 0
			end as haber,
			case
				when sum(case when a1.debe > a1.haber then a1.debe-a1.haber else  0 end) < sum(case when a1.haber> a1.debe then a1.haber-a1.debe else 0 end)
				then sum(case when a1.haber> a1.debe then a1.haber-a1.debe else 0 end) - sum(case when a1.debe > a1.haber then a1.debe-a1.haber else  0 end)
				else 0
			end as saldo_deudor,
			case
				when sum(case when a1.debe > a1.haber then a1.debe-a1.haber else  0 end) > sum(case when a1.haber> a1.debe then a1.haber-a1.debe else 0 end)
				then sum(case when a1.debe > a1.haber then a1.debe-a1.haber else  0 end) - sum(case when a1.haber> a1.debe then a1.haber-a1.debe else 0 end)
				else 0
			end as saldo_acreedor,
			case
				when sum(case when a2.clasification_sheet='0' and a1.debe>a1.haber then a1.debe-a1.haber else 0 end) < sum(case when a2.clasification_sheet='0' and a1.haber>a1.debe then a1.haber-a1.debe else 0 end)
				then sum(case when a2.clasification_sheet='0' and a1.haber>a1.debe then a1.haber-a1.debe else 0 end) - sum(case when a2.clasification_sheet='0' and a1.debe>a1.haber then a1.debe-a1.haber else 0 end)
				else 0
			end as activo,
			case
				when sum(case when a2.clasification_sheet='0' and a1.debe>a1.haber then a1.debe-a1.haber else 0 end) > sum(case when a2.clasification_sheet='0' and a1.haber>a1.debe then a1.haber-a1.debe else 0 end)
				then sum(case when a2.clasification_sheet='0' and a1.debe>a1.haber then a1.debe-a1.haber else 0 end) - sum(case when a2.clasification_sheet='0' and a1.haber>a1.debe then a1.haber-a1.debe else 0 end)
				else 0
			end as pasivo,
			case
				when sum(case when (a2.clasification_sheet='1' or a2.clasification_sheet='3') and a1.debe>a1.haber then a1.debe-a1.haber else 0 end) < sum(case when (a2.clasification_sheet='1' or a2.clasification_sheet='3') and a1.haber>a1.debe then a1.haber-a1.debe else 0 end)
				then sum(case when (a2.clasification_sheet='1' or a2.clasification_sheet='3') and a1.haber>a1.debe then a1.haber-a1.debe else 0 end) - sum(case when (a2.clasification_sheet='1' or a2.clasification_sheet='3') and a1.debe>a1.haber then a1.debe-a1.haber else 0 end)
				else 0
			end as perdinat,
			case
				when sum(case when (a2.clasification_sheet='1' or a2.clasification_sheet='3') and a1.debe>a1.haber then a1.debe-a1.haber else 0 end) > sum(case when (a2.clasification_sheet='1' or a2.clasification_sheet='3') and a1.haber>a1.debe then a1.haber-a1.debe else 0 end)
				then sum(case when (a2.clasification_sheet='1' or a2.clasification_sheet='3') and a1.debe>a1.haber then a1.debe-a1.haber else 0 end) - sum(case when (a2.clasification_sheet='1' or a2.clasification_sheet='3') and a1.haber>a1.debe then a1.haber-a1.debe else 0 end)
				else 0
			end as ganannat,
			case
				when sum(case when (a2.clasification_sheet='2' or a2.clasification_sheet='3') and a1.debe>a1.haber then a1.debe-a1.haber else 0 end) < sum(case when (a2.clasification_sheet='2' or a2.clasification_sheet='3') and a1.haber>a1.debe then a1.haber-a1.debe else 0 end)
				then sum(case when (a2.clasification_sheet='2' or a2.clasification_sheet='3') and a1.haber>a1.debe then a1.haber-a1.debe else 0 end) - sum(case when (a2.clasification_sheet='2' or a2.clasification_sheet='3') and a1.debe>a1.haber then a1.debe-a1.haber else 0 end)
				else 0
			end as perdifun,
			case
				when sum(case when (a2.clasification_sheet='2' or a2.clasification_sheet='3') and a1.debe>a1.haber then a1.debe-a1.haber else 0 end) > sum(case when (a2.clasification_sheet='2' or a2.clasification_sheet='3') and a1.haber>a1.debe then a1.haber-a1.debe else 0 end)
				then sum(case when (a2.clasification_sheet='2' or a2.clasification_sheet='3') and a1.debe>a1.haber then a1.debe-a1.haber else 0 end) - sum(case when (a2.clasification_sheet='2' or a2.clasification_sheet='3') and a1.haber>a1.debe then a1.haber-a1.debe else 0 end)
				else 0
			end as gananfun
			from get_sumas_mayor_f2('{date_from}','{date_to}',{company_id}) a1
			left join account_account a2 on a2.id=a1.account_id))T
		""".format(
				date_from = self.period_id.date_start.strftime('%Y/%m/%d'),
				date_to = self.period_id.date_end.strftime('%Y/%m/%d'),
				company_id = self.company_id.id
			)
		return sql

	def _get_f2_balance_sql(self):
		sql = """
			select 
			'{date_from}'::date as date_from,
			'{date_to}'::date as date_to, T.* FROM(
			(select
			a2.code_prefix_start as cuenta,
			a2.name as nomenclatura,
			a1.si_debe,
			a1.si_haber,
			a1.debe,
			a1.haber,
			case when a1.debe > a1.haber then a1.debe-a1.haber else  0 end as saldo_deudor,
			case when a1.haber> a1.debe then a1.haber-a1.debe else 0 end as saldo_acreedor,
			case when a2.clasification_sheet='0' and a1.debe>a1.haber then a1.debe-a1.haber else 0 end as activo,
			case when a2.clasification_sheet='0' and a1.haber>a1.debe then a1.haber-a1.debe else 0 end as pasivo,
			case when (a2.clasification_sheet='1' or a2.clasification_sheet='3') and a1.debe>a1.haber then a1.debe-a1.haber else 0 end as perdinat,
			case when (a2.clasification_sheet='1' or a2.clasification_sheet='3') and a1.haber>a1.debe then a1.haber-a1.debe else 0 end as ganannat,
			case when (a2.clasification_sheet='2' or a2.clasification_sheet='3') and a1.debe>a1.haber then a1.debe-a1.haber else 0 end as perdifun,
			case when (a2.clasification_sheet='2' or a2.clasification_sheet='3') and a1.haber>a1.debe then a1.haber-a1.debe else 0 end as gananfun
			from get_sumas_balance_f2('{date_from}','{date_to}',{company_id}) a1
			left join account_group a2 on a2.id=a1.account_id
			order by a2.code_prefix_start)
			UNION ALL
			(SELECT 
			null::text as mayor,
			'SUMAS'::text as nomenclatura,
			sum(a1.si_debe) as si_debe,
			sum(a1.si_haber) as si_haber,
			sum(a1.debe) as debe,
			sum(a1.haber) as haber,
			sum(case when a1.debe > a1.haber then a1.debe-a1.haber else  0 end) as saldo_deudor,
			sum(case when a1.haber> a1.debe then a1.haber-a1.debe else 0 end) as saldo_acreedor,
			sum(case when a2.clasification_sheet='0' and a1.debe>a1.haber then a1.debe-a1.haber else 0 end) as activo,
			sum(case when a2.clasification_sheet='0' and a1.haber>a1.debe then a1.haber-a1.debe else 0 end) as pasivo,
			sum(case when (a2.clasification_sheet='1' or a2.clasification_sheet='3') and a1.debe>a1.haber then a1.debe-a1.haber else 0 end) as perdinat,
			sum(case when (a2.clasification_sheet='1' or a2.clasification_sheet='3') and a1.haber>a1.debe then a1.haber-a1.debe else 0 end) as ganannat,
			sum(case when (a2.clasification_sheet='2' or a2.clasification_sheet='3') and a1.debe>a1.haber then a1.debe-a1.haber else 0 end) as perdifun,
			sum(case when (a2.clasification_sheet='2' or a2.clasification_sheet='3') and a1.haber>a1.debe then a1.haber-a1.debe else 0 end) as gananfun
			from get_sumas_balance_f2('{date_from}','{date_to}',{company_id}) a1
			left join account_group a2 on a2.id=a1.account_id)
			UNION ALL
			(SELECT 
			null::text as mayor,
			'UTILIDAD O PERDIDA'::text as nomenclatura,
			case
				when sum(a1.si_debe) < sum(a1.si_haber)
				then sum(a1.si_haber) - sum(a1.si_debe)
				else 0
			end as si_debe,
			case
				when sum(a1.si_debe) > sum(a1.si_haber)
				then sum(a1.si_debe) - sum(a1.si_haber) 
				else 0
			end as si_haber,
			case
				when sum(a1.debe) < sum(a1.haber)
				then sum(a1.haber) - sum(a1.debe)
				else 0
			end as debe,
			case
				when sum(a1.debe) > sum(a1.haber)
				then sum(a1.debe) - sum(a1.haber) 
				else 0
			end as haber,
			case
				when sum(case when a1.debe > a1.haber then a1.debe-a1.haber else  0 end) < sum(case when a1.haber> a1.debe then a1.haber-a1.debe else 0 end)
				then sum(case when a1.haber> a1.debe then a1.haber-a1.debe else 0 end) - sum(case when a1.debe > a1.haber then a1.debe-a1.haber else  0 end)
				else 0
			end as saldo_deudor,
			case
				when sum(case when a1.debe > a1.haber then a1.debe-a1.haber else  0 end) > sum(case when a1.haber> a1.debe then a1.haber-a1.debe else 0 end)
				then sum(case when a1.debe > a1.haber then a1.debe-a1.haber else  0 end) - sum(case when a1.haber> a1.debe then a1.haber-a1.debe else 0 end)
				else 0
			end as saldo_acreedor,
			case
				when sum(case when a2.clasification_sheet='0' and a1.debe>a1.haber then a1.debe-a1.haber else 0 end) < sum(case when a2.clasification_sheet='0' and a1.haber>a1.debe then a1.haber-a1.debe else 0 end)
				then sum(case when a2.clasification_sheet='0' and a1.haber>a1.debe then a1.haber-a1.debe else 0 end) - sum(case when a2.clasification_sheet='0' and a1.debe>a1.haber then a1.debe-a1.haber else 0 end)
				else 0
			end as activo,
			case
				when sum(case when a2.clasification_sheet='0' and a1.debe>a1.haber then a1.debe-a1.haber else 0 end) > sum(case when a2.clasification_sheet='0' and a1.haber>a1.debe then a1.haber-a1.debe else 0 end)
				then sum(case when a2.clasification_sheet='0' and a1.debe>a1.haber then a1.debe-a1.haber else 0 end) - sum(case when a2.clasification_sheet='0' and a1.haber>a1.debe then a1.haber-a1.debe else 0 end)
				else 0
			end as pasivo,
			case
				when sum(case when (a2.clasification_sheet='1' or a2.clasification_sheet='3') and a1.debe>a1.haber then a1.debe-a1.haber else 0 end) < sum(case when (a2.clasification_sheet='1' or a2.clasification_sheet='3') and a1.haber>a1.debe then a1.haber-a1.debe else 0 end)
				then sum(case when (a2.clasification_sheet='1' or a2.clasification_sheet='3') and a1.haber>a1.debe then a1.haber-a1.debe else 0 end) - sum(case when (a2.clasification_sheet='1' or a2.clasification_sheet='3') and a1.debe>a1.haber then a1.debe-a1.haber else 0 end)
				else 0
			end as perdinat,
			case
				when sum(case when (a2.clasification_sheet='1' or a2.clasification_sheet='3') and a1.debe>a1.haber then a1.debe-a1.haber else 0 end) > sum(case when (a2.clasification_sheet='1' or a2.clasification_sheet='3') and a1.haber>a1.debe then a1.haber-a1.debe else 0 end)
				then sum(case when (a2.clasification_sheet='1' or a2.clasification_sheet='3') and a1.debe>a1.haber then a1.debe-a1.haber else 0 end) - sum(case when (a2.clasification_sheet='1' or a2.clasification_sheet='3') and a1.haber>a1.debe then a1.haber-a1.debe else 0 end)
				else 0
			end as ganannat,
			case
				when sum(case when (a2.clasification_sheet='2' or a2.clasification_sheet='3') and a1.debe>a1.haber then a1.debe-a1.haber else 0 end) < sum(case when (a2.clasification_sheet='2' or a2.clasification_sheet='3') and a1.haber>a1.debe then a1.haber-a1.debe else 0 end)
				then sum(case when (a2.clasification_sheet='2' or a2.clasification_sheet='3') and a1.haber>a1.debe then a1.haber-a1.debe else 0 end) - sum(case when (a2.clasification_sheet='2' or a2.clasification_sheet='3') and a1.debe>a1.haber then a1.debe-a1.haber else 0 end)
				else 0
			end as perdifun,
			case
				when sum(case when (a2.clasification_sheet='2' or a2.clasification_sheet='3') and a1.debe>a1.haber then a1.debe-a1.haber else 0 end) > sum(case when (a2.clasification_sheet='2' or a2.clasification_sheet='3') and a1.haber>a1.debe then a1.haber-a1.debe else 0 end)
				then sum(case when (a2.clasification_sheet='2' or a2.clasification_sheet='3') and a1.debe>a1.haber then a1.debe-a1.haber else 0 end) - sum(case when (a2.clasification_sheet='2' or a2.clasification_sheet='3') and a1.haber>a1.debe then a1.haber-a1.debe else 0 end)
				else 0
			end as gananfun
			from get_sumas_balance_f2('{date_from}','{date_to}',{company_id}) a1
			left join account_group a2 on a2.id=a1.account_id))T
		""".format(
				date_from = self.period_id.date_start.strftime('%Y/%m/%d'),
				date_to = self.period_id.date_end.strftime('%Y/%m/%d'),
				company_id = self.company_id.id
			)
		return sql

	def get_report(self):
		if self.type_show == 'pantalla':
			if self.level == 'register':
				self._cr.execute("""
				DROP VIEW IF EXISTS f2_register;
				CREATE OR REPLACE VIEW f2_register AS 
				(SELECT row_number() OVER () AS id, T.* FROM (%s) T)
				"""%(self._get_f2_register_sql()))
				return self.get_window_f2_register()
			else:
				self._cr.execute("""
				DROP VIEW IF EXISTS f2_balance;
				CREATE OR REPLACE VIEW f2_balance AS 
				(SELECT row_number() OVER () AS id, T.* FROM (%s) T)
				"""%(self._get_f2_balance_sql()))
				return self.get_window_f2_balance()
		else:
			return self.get_excel_f2_register() if self.level == 'register' else self.get_excel_f2_balance()
	
	def get_window_f2_register(self):
		view = self.env.ref('account_htf2_report.view_f2_register_tree').id
		return {
			'name': 'Hoja de Trabajo F2 - Registro',
			'type': 'ir.actions.act_window',
			'res_model': 'f2.register',
			'view_mode': 'tree',
			'views': [(view, 'tree')],
		}

	def get_window_f2_balance(self):
		view = self.env.ref('account_htf2_report.view_f2_balance_tree').id
		return {
			'name': 'Hoja de Trabajo F2 - Balance',
			'type': 'ir.actions.act_window',
			'res_model': 'f2.balance',
			'view_mode': 'tree',
			'views': [(view, 'tree')],
		}

	def get_excel_f2_register(self):
		import io
		from xlsxwriter.workbook import Workbook
		from xlsxwriter.utility import xl_rowcol_to_cell
		ReportBase = self.env['report.base']
		direccion = self.env['account.main.parameter'].search([('company_id','=',self.company_id.id)],limit=1).dir_create_file

		if not direccion:
			raise UserError(u'No existe un Directorio Exportadores configurado en Parametros Principales de Contabilidad para su Compañía')

		workbook = Workbook(direccion +'Hoja_Trabajo_F2.xlsx')
		workbook, formats = ReportBase.get_formats(workbook)

		import importlib
		import sys
		importlib.reload(sys)

		worksheet = workbook.add_worksheet("Hoja de Trabajo F2")
		worksheet.set_tab_color('blue')

		HEADERS = ['MAYOR','CUENTA','NOMENCLATURA','DEBE INICIAL','HABER INICIAL','DEBE','HABER','SALDO DEUDOR','SALDO ACREEDOR',
				   'ACTIVO','PASIVO','PERDINAT','GANANNAT','PERDIFUN','GANANFUN']
		worksheet = ReportBase.get_headers(worksheet,HEADERS,0,0,formats['boldbord'])
		x=1

		self.env.cr.execute(self._get_f2_register_sql())
		res = self.env.cr.dictfetchall()
		total = len(res)-2

		for c,line in enumerate(res):
			worksheet.write(x,0,line['mayor'] if line['mayor'] else '',formats['especial1'])
			worksheet.write(x,1,line['cuenta'] if line['cuenta'] else '',formats['especial1'])
			worksheet.write(x,2,line['nomenclatura'] if line['nomenclatura'] else '',formats['especial1'] if c < total else formats['boldbord'])
			worksheet.write(x,3,line['si_debe'] if line['si_debe'] else 0,formats['numberdos'] if c < total else formats['numbertotal'])
			worksheet.write(x,4,line['si_haber'] if line['si_haber'] else 0,formats['numberdos'] if c < total else formats['numbertotal'])
			worksheet.write(x,5,line['debe'] if line['debe'] else 0,formats['numberdos'] if c < total else formats['numbertotal'])
			worksheet.write(x,6,line['haber'] if line['haber'] else 0,formats['numberdos'] if c < total else formats['numbertotal'])
			worksheet.write(x,7,line['saldo_deudor'] if line['saldo_deudor'] else 0,formats['numberdos'] if c < total else formats['numbertotal'])
			worksheet.write(x,8,line['saldo_acreedor'] if line['saldo_acreedor'] else 0,formats['numberdos'] if c < total else formats['numbertotal'])
			worksheet.write(x,9,line['activo'] if line['activo'] else 0,formats['numberdos'] if c < total else formats['numbertotal'])
			worksheet.write(x,10,line['pasivo'] if line['pasivo'] else 0,formats['numberdos'] if c < total else formats['numbertotal'])
			worksheet.write(x,11,line['perdinat'] if line['perdinat'] else 0,formats['numberdos'] if c < total else formats['numbertotal'])
			worksheet.write(x,12,line['ganannat'] if line['ganannat'] else 0,formats['numberdos'] if c < total else formats['numbertotal'])
			worksheet.write(x,13,line['perdifun'] if line['perdifun'] else 0,formats['numberdos'] if c < total else formats['numbertotal'])
			worksheet.write(x,14,line['gananfun'] if line['gananfun'] else 0,formats['numberdos'] if c < total else formats['numbertotal'])
			x += 1

		widths = [7,9,40,10,10,10,10,10,10,10,10,10,10,10,10]
		worksheet = ReportBase.resize_cells(worksheet,widths)
		workbook.close()
		f = open(direccion +'Hoja_Trabajo_F2.xlsx', 'rb')
		return self.env['popup.it'].get_file('Hoja Trabajo F2 - Registro.xlsx',base64.encodestring(b''.join(f.readlines())))

	def get_excel_f2_balance(self):
		import io
		from xlsxwriter.workbook import Workbook
		from xlsxwriter.utility import xl_rowcol_to_cell
		ReportBase = self.env['report.base']
		direccion = self.env['account.main.parameter'].search([('company_id','=',self.company_id.id)],limit=1).dir_create_file

		if not direccion:
			raise UserError(u'No existe un Directorio Exportadores configurado en Parametros Principales de Contabilidad para su Compañía')

		workbook = Workbook(direccion +'Hoja_Trabajo_F2.xlsx')
		workbook, formats = ReportBase.get_formats(workbook)

		import importlib
		import sys
		importlib.reload(sys)

		worksheet = workbook.add_worksheet("Hoja de Trabajo F2")
		worksheet.set_tab_color('blue')

		HEADERS = ['CUENTA','NOMENCLATURA','DEBE INICIAL','HABER INICIAL','DEBE','HABER','SALDO DEUDOR','SALDO ACREEDOR',
				   'ACTIVO','PASIVO','PERDINAT','GANANNAT','PERDIFUN','GANANFUN']
		worksheet = ReportBase.get_headers(worksheet,HEADERS,0,0,formats['boldbord'])
		x=1

		self.env.cr.execute(self._get_f2_balance_sql())
		res = self.env.cr.dictfetchall()
		total = len(res)-2

		for c,line in enumerate(res):
			worksheet.write(x,0,line['cuenta'] if line['cuenta'] else '',formats['especial1'])
			worksheet.write(x,1,line['nomenclatura'] if line['nomenclatura'] else '',formats['especial1'] if c < total else formats['boldbord'])
			worksheet.write(x,2,line['si_debe'] if line['si_debe'] else 0,formats['numberdos'] if c < total else formats['numbertotal'])
			worksheet.write(x,3,line['si_haber'] if line['si_haber'] else 0,formats['numberdos'] if c < total else formats['numbertotal'])
			worksheet.write(x,4,line['debe'] if line['debe'] else 0,formats['numberdos'] if c < total else formats['numbertotal'])
			worksheet.write(x,5,line['haber'] if line['haber'] else 0,formats['numberdos'] if c < total else formats['numbertotal'])
			worksheet.write(x,6,line['saldo_deudor'] if line['saldo_deudor'] else 0,formats['numberdos'] if c < total else formats['numbertotal'])
			worksheet.write(x,7,line['saldo_acreedor'] if line['saldo_acreedor'] else 0,formats['numberdos'] if c < total else formats['numbertotal'])
			worksheet.write(x,8,line['activo'] if line['activo'] else 0,formats['numberdos'] if c < total else formats['numbertotal'])
			worksheet.write(x,9,line['pasivo'] if line['pasivo'] else 0,formats['numberdos'] if c < total else formats['numbertotal'])
			worksheet.write(x,10,line['perdinat'] if line['perdinat'] else 0,formats['numberdos'] if c < total else formats['numbertotal'])
			worksheet.write(x,11,line['ganannat'] if line['ganannat'] else 0,formats['numberdos'] if c < total else formats['numbertotal'])
			worksheet.write(x,12,line['perdifun'] if line['perdifun'] else 0,formats['numberdos'] if c < total else formats['numbertotal'])
			worksheet.write(x,13,line['gananfun'] if line['gananfun'] else 0,formats['numberdos'] if c < total else formats['numbertotal'])
			x += 1
		widths = [9,40,10,10,10,10,10,10,10,10,10,10,10,10]
		worksheet = ReportBase.resize_cells(worksheet,widths)
		workbook.close()
		f = open(direccion +'Hoja_Trabajo_F2.xlsx', 'rb')
		return self.env['popup.it'].get_file('Hoja Trabajo F2 - Balance.xlsx',base64.encodestring(b''.join(f.readlines())))