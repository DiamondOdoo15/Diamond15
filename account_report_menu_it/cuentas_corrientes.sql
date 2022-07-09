DROP FUNCTION IF EXISTS public.provisiones(date,date,integer,character varying) CASCADE;

CREATE OR REPLACE FUNCTION public.provisiones(
	date_from date,
	date_to date,
	company_id integer,
	type character varying)
    RETURNS TABLE(account_id integer, partner_id integer, type_document_id integer, nro_comp character varying, min integer) 
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE 
    ROWS 1000
AS $BODY$
BEGIN
	RETURN QUERY 

SELECT account_move_line.account_id,
    account_move_line.partner_id,
    account_move_line.type_document_id,
    account_move_line.nro_comp,
    min(account_move_line.id) AS min
   FROM account_move_line
	left join account_move am on am.id=account_move_line.move_id
	left join account_account aa on aa.id = account_move_line.account_id
  WHERE aa.internal_type = 'receivable' AND account_move_line.debit <> 0
  AND am.state = 'posted' AND ((case when $4= 'date' then am.date else am.invoice_date end) BETWEEN $1 and $2) AND am.company_id = $3
  GROUP BY account_move_line.account_id, account_move_line.partner_id, account_move_line.type_document_id, account_move_line.nro_comp
UNION ALL
 SELECT account_move_line.account_id,
    account_move_line.partner_id,
    account_move_line.type_document_id,
    account_move_line.nro_comp,
    min(account_move_line.id) AS min
   FROM account_move_line
	left join account_move am on am.id=account_move_line.move_id
	left join account_account aa on aa.id = account_move_line.account_id
  WHERE aa.internal_type = 'payable' AND account_move_line.credit <> 0
  AND am.state = 'posted' AND ((case when $4= 'date' then am.date else am.invoice_date end) BETWEEN $1 and $2) AND am.company_id = $3
  GROUP BY account_move_line.account_id, account_move_line.partner_id, account_move_line.type_document_id, account_move_line.nro_comp;
  END;
$BODY$;
----------------------------------------------------------------------------------------------------------------------------------------------------
DROP FUNCTION IF EXISTS public.saldos(date,date,integer,character varying) CASCADE;

CREATE OR REPLACE FUNCTION public.saldos(
	date_from date,
	date_to date,
	company_id integer,
	type character varying)
    RETURNS TABLE(account_id integer, partner_id integer, type_document_id integer, nro_comp character varying, aml_ids integer[], debe numeric, haber numeric, saldo_mn numeric, saldo_me numeric) 
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE 
    ROWS 1000
AS $BODY$
BEGIN
	RETURN QUERY 
	SELECT account_move_line.account_id,
    account_move_line.partner_id,
    account_move_line.type_document_id,
    account_move_line.nro_comp,
	array_agg(account_move_line.id) as aml_ids,
    sum(account_move_line.debit) AS debe,
    sum(account_move_line.credit) AS haber,
    sum(account_move_line.balance) AS saldo_mn,
    sum(account_move_line.amount_currency) AS saldo_me
   FROM account_move_line
	left join account_move am on am.id=account_move_line.move_id
	left join account_account aa on aa.id = account_move_line.account_id
  WHERE aa.internal_type in ('payable','receivable')
  AND am.state = 'posted' AND ((case when $4= 'date' then am.date else am.invoice_date end) BETWEEN $1 and $2) AND am.company_id = $3
  GROUP BY account_move_line.partner_id, account_move_line.account_id, account_move_line.type_document_id, account_move_line.nro_comp;
END;
$BODY$;
----------------------------------------------------------------------------------------------------------------------------------------------------


DROP FUNCTION IF EXISTS public.get_saldos(date,date,integer,character varying) CASCADE;

CREATE OR REPLACE FUNCTION public.get_saldos(
	date_from date,
	date_to date,
	id_company integer,
	type character varying)
    RETURNS TABLE(id bigint, periodo text, fecha_con text, libro character varying, voucher character varying, td_partner character varying, 
	doc_partner character varying, partner character varying, td_sunat character varying, nro_comprobante character varying, fecha_doc date, 
	fecha_ven date, cuenta character varying, moneda character varying, debe numeric, haber numeric, saldo_mn numeric, saldo_me numeric,
	aml_ids integer[], journal_id integer, account_id integer, partner_id integer, move_id integer, move_line_id integer, company_id integer) 
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE 
    ROWS 1000
AS $BODY$
BEGIN
	RETURN QUERY 
	SELECT row_number() OVER () AS id,t.*
		   FROM ( select 
	CASE
		WHEN am.is_opening_close = true AND to_char(am.date::timestamp with time zone, 'mmdd'::text) = '0101'::text THEN to_char(am.date::timestamp with time zone, 'yyyy'::text) || '00'::text
		WHEN am.is_opening_close = true AND to_char(am.date::timestamp with time zone, 'mmdd'::text) = '1231'::text THEN to_char(am.date::timestamp with time zone, 'yyyy'::text) || '13'::text
		ELSE to_char(am.date::timestamp with time zone, 'yyyymm'::text)
	END AS periodo,
	to_char(am.date::timestamp with time zone, 'yyyy/mm/dd'::text) AS fecha_con,
	aj.code as libro, 
	am.name as voucher, 
	latiden.code_sunat AS td_partner,
	rp.vat as doc_partner, 
	rp.name as partner, 
	ec1.code as td_sunat,
	p.nro_comp as nro_comprobante, 
	am.invoice_date as fecha_doc,
	aml.date_maturity as fecha_ven,
	aa.code as cuenta,
	rc.name as moneda,
	s.debe,s.haber,s.saldo_mn,s.saldo_me ,
	s.aml_ids,
	am.journal_id,
	aml.account_id,
	aml.partner_id,
	aml.move_id,
	p.min as min_line_id,
	am.company_id
	from saldos($1,$2,$3,$4) s
	left join provisiones($1,$2,$3,$4) p on 
	p.account_id=s.account_id and
	p.partner_id=s.partner_id and
	p.type_document_id=s.type_document_id and
	p.nro_comp=s.nro_comp
	left join account_move_line aml on aml.id=p.min
	left join account_move am on am.id=aml.move_id
	left join account_account aa on aa.id=p.account_id
	left join account_journal aj on aj.id=am.journal_id
	left join res_partner rp on rp.id=p.partner_id
	LEFT JOIN l10n_latam_identification_type latiden ON latiden.id = rp.l10n_latam_identification_type_id
	LEFT JOIN l10n_latam_document_type ec1 ON ec1.id = aml.type_document_id
	LEFT JOIN res_currency rc ON rc.id = aml.currency_id
	order by rp.vat,aa.code,p.nro_comp) t;
	END;
$BODY$;


---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
DROP FUNCTION IF EXISTS public.get_saldo_detalle(date, date, integer) CASCADE;

CREATE OR REPLACE FUNCTION public.get_saldo_detalle(
	date_from date,
	date_to date,
	company_id integer)
	RETURNS TABLE(periodo character varying, fecha date, libro character varying, voucher character varying,td_partner character varying, doc_partner character varying, partner character varying, td_sunat character varying, nro_comprobante character varying, fecha_doc date, fecha_ven date, cuenta character varying, moneda character varying, debe numeric, haber numeric,balance numeric,importe_me numeric, saldo numeric, saldo_me numeric, partner_id integer, account_id integer) AS
	$BODY$
	BEGIN
	RETURN QUERY 
select 
CASE
	WHEN am.is_opening_close = true AND to_char(am.date::timestamp with time zone, 'mmdd'::text) = '0101'::text THEN (to_char(am.date::timestamp with time zone, 'yyyy'::text) || '00')::character varying
	WHEN am.is_opening_close = true AND to_char(am.date::timestamp with time zone, 'mmdd'::text) = '1231'::text THEN (to_char(am.date::timestamp with time zone, 'yyyy'::text) || '13')::character varying
	ELSE to_char(am.date::timestamp with time zone, 'yyyymm'::text)::character varying
END AS periodo,
T.fecha,
aj.code as libro,
am.name AS voucher,
llit.code_sunat as td_partner,
rp.vat as doc_partner,
rp.name as partner,
lldt.code as td_sunat,
aml.nro_comp as nro_comprobante,
am.invoice_date AS fecha_doc,
aml.date_maturity AS fecha_ven,
aa.code as cuenta,
rc.name as moneda,
T.debit as debe,
T.credit as haber,
T.balance,
T.balance_me as importe_me,
sum(coalesce(T.balance,0)) OVER (partition by aml.partner_id, T.account_id,lldt.code, aml.nro_comp order by aml.partner_id, T.account_id,lldt.code, aml.nro_comp, T.fecha) as saldo,
sum(coalesce(T.balance_me,0)) OVER (partition by aml.partner_id, T.account_id,lldt.code, aml.nro_comp order by aml.partner_id, T.account_id,lldt.code, aml.nro_comp, T.fecha) as saldo_me,
aml.partner_id,
T.account_id from (
select 
am.id as move_id,
aml.id as move_line_id,
am.date as fecha,
aml.account_id,
aml.debit,
aml.credit,
coalesce(aml.balance,0) as balance,
aml.amount_currency as balance_me
from account_move_line aml
left join account_move am on am.id=aml.move_id
LEFT JOIN account_account aa ON aa.id = aml.account_id
where (am.date between date_from and date_to)
and  am.state='posted'
and aml.display_type is NULL
and aa.is_document_an = True
and am.company_id=$3
)T
LEFT JOIN account_move_line aml ON T.move_line_id = aml.id
LEFT JOIN account_move am ON T.move_id = am.id
LEFT JOIN account_journal aj ON aj.id = am.journal_id
LEFT JOIN account_account aa ON aa.id = T.account_id
LEFT JOIN res_currency rc ON rc.id = aml.currency_id
LEFT JOIN res_partner rp ON rp.id = aml.partner_id
LEFT JOIN l10n_latam_identification_type llit ON llit.id = rp.l10n_latam_identification_type_id
LEFT JOIN l10n_latam_document_type lldt ON lldt.id = aml.type_document_id
order by aml.partner_id, T.account_id,lldt.code, aml.nro_comp, T.fecha;
END;
	$BODY$
	LANGUAGE plpgsql VOLATILE
	COST 100
	ROWS 1000;

---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
DROP FUNCTION IF EXISTS public.get_saldos_me_global(character varying,character varying,integer) CASCADE;

CREATE OR REPLACE FUNCTION public.get_saldos_me_global(
    periodo_apertura character varying,
    periodo character varying,
    company_id integer)
    RETURNS TABLE(account_id integer, debe numeric, haber numeric, saldomn numeric, saldome numeric) 
    LANGUAGE 'plpgsql'

    COST 100
    VOLATILE 
    ROWS 1000
AS $BODY$
BEGIN
    RETURN QUERY   
    SELECT a1.account_id,
        sum(a1.debe) AS debe,
        sum(a1.haber) AS haber,
        sum(coalesce(a1.balance,0)) AS saldomn,
        sum(coalesce(a1.importe_me,0)) AS saldome
        FROM get_diariog((select date_start from account_period where code = $1::character varying limit 1),(select date_end from account_period where code = $2::character varying  limit 1),$3) a1
        LEFT JOIN account_account a2 ON a2.id = a1.account_id
        LEFT JOIN res_currency a4 on a4.id = a2.currency_id
        WHERE a4.name = 'USD' AND
        a2.dif_cambio_type = 'global' AND (a1.periodo::integer between $1::integer and $2::integer)
        GROUP BY a1.account_id;
END;
$BODY$;
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
DROP FUNCTION IF EXISTS public.get_saldos_me_global_2(character varying,character varying,integer) CASCADE;

CREATE OR REPLACE FUNCTION public.get_saldos_me_global_2(
	periodo_apertura character varying,
	periodo character varying,
	company_id integer)
    RETURNS TABLE(account_id integer, debe numeric, haber numeric, saldomn numeric, saldome numeric, group_balance character varying, tc numeric) 
    LANGUAGE 'plpgsql'

    COST 100
    VOLATILE 
    ROWS 1000
AS $BODY$
BEGIN
	RETURN QUERY  
 SELECT
    b1.account_id,
    b1.debe,
    b1.haber,
    b1.saldomn,
    b1.saldome,
    b3.group_balance,
        CASE
            WHEN b3.group_balance::text = ANY (ARRAY['B1'::character varying, 'B2'::character varying]::text[]) THEN ( SELECT edcl.compra
               FROM exchange_diff_config_line edcl
                 LEFT JOIN exchange_diff_config edc ON edc.id = edcl.line_id
                 LEFT JOIN account_period ap ON ap.id = edcl.period_id
              WHERE edc.company_id = $3 AND ap.code::text = $2::text)
            ELSE ( SELECT edcl.venta
               FROM exchange_diff_config_line edcl
                 LEFT JOIN exchange_diff_config edc ON edc.id = edcl.line_id
                 LEFT JOIN account_period ap ON ap.id = edcl.period_id
              WHERE edc.company_id = $3 AND ap.code::text = $2::text)
        END AS tc
   FROM get_saldos_me_global($1,$2,$3) b1
     LEFT JOIN account_account b2 ON b2.id = b1.account_id
     LEFT JOIN account_type_it b3 ON b3.id = b2.account_type_it_id;
END;
$BODY$;

----------------------------------------------------------------------------------------------------------------------------------------------------------
DROP FUNCTION IF EXISTS public.get_saldos_me_global_final(character varying,character varying,integer) CASCADE;

CREATE OR REPLACE FUNCTION public.get_saldos_me_global_final(
	fiscal_year character varying,
	periodo character varying,
	company_id integer)
    RETURNS TABLE(account_id integer, debe numeric, haber numeric, saldomn numeric, saldome numeric, group_balance character varying, tc numeric, saldo_act numeric, diferencia numeric, difference_account_id integer) 
    LANGUAGE 'plpgsql'

    COST 100
    VOLATILE 
    ROWS 1000
AS $BODY$
BEGIN
	RETURN QUERY  
	SELECT *,
	round(coalesce(vst.tc,0) * vst.saldome,2) AS saldo_act,
	vst.saldomn - round(coalesce(vst.tc,0) * vst.saldome,2) AS diferencia,
	CASE 
	WHEN vst.saldomn < round(vst.tc * vst.saldome,2) AND vst.group_balance IN ('B1','B2') THEN (SELECT edc.profit_account_id FROM exchange_diff_config edc WHERE edc.company_id = $3)
	WHEN vst.saldomn > round(vst.tc * vst.saldome,2) AND vst.group_balance IN ('B1','B2') THEN (SELECT edc.loss_account_id FROM exchange_diff_config edc WHERE edc.company_id = $3)
	WHEN (-1 * vst.saldomn) > (-1 * round(vst.tc * vst.saldome,2)) AND vst.group_balance IN ('B3','B4','B5') THEN (SELECT edc.profit_account_id FROM exchange_diff_config edc WHERE edc.company_id = $3)
	WHEN (-1 * vst.saldomn) < (-1 * round(vst.tc * vst.saldome,2)) AND vst.group_balance IN ('B3','B4','B5') THEN (SELECT edc.loss_account_id FROM exchange_diff_config edc WHERE edc.company_id = $3) END AS difference_account_id
	FROM get_saldos_me_global_2($1||'00',$2,$3) vst;
END;
$BODY$;

----------------------------------------------------------------------------------------------------------------------------------------------------------
DROP FUNCTION IF EXISTS public.get_saldos_me_documento(character varying,character varying,integer) CASCADE;

CREATE OR REPLACE FUNCTION public.get_saldos_me_documento(
	periodo_apertura character varying,
	periodo character varying,
	company_id integer)
    RETURNS TABLE(partner_id integer, account_id integer, td_sunat character varying, nro_comprobante character varying, debe numeric, haber numeric, saldomn numeric, saldome numeric) 
    LANGUAGE 'plpgsql'

    COST 100
    VOLATILE 
    ROWS 1000
AS $BODY$
BEGIN
	RETURN QUERY   
	select a1.partner_id,
	a1.account_id,
	a1.td_sunat,
	a1.nro_comprobante,
	sum(a1.debe) debe,
	sum(a1.haber) haber,
	sum(coalesce(a1.balance,0))as saldomn,
	sum(coalesce(a1.importe_me,0)) as saldome 
	from get_diariog((select date_start from account_period where code = $1::character varying limit 1),(select date_end from account_period where code = $2::character varying  limit 1),$3) a1
	left join account_account a2 on a2.id=a1.account_id
	left join account_type_it a3 on a3.id=a2.account_type_it_id
	left join res_currency a4 on a4.id = a2.currency_id
	where 
	a2.dif_cambio_type = 'doc' and
	a4.name = 'USD' and
	(a1.periodo::int between $1::int and $2::int)
	group by a1.partner_id,a1.account_id,a1.td_sunat,a1.nro_comprobante
	having (sum(a1.balance)+sum(a1.importe_me)) <> 0;
END;
$BODY$;

----------------------------------------------------------------------------------------------------------------------------------------------------------
DROP FUNCTION IF EXISTS public.get_saldos_me_documento_2(character varying,character varying,integer) CASCADE;

CREATE OR REPLACE FUNCTION public.get_saldos_me_documento_2(
	periodo_apertura character varying,
	periodo character varying,
	company_id integer)
    RETURNS TABLE(partner_id integer, account_id integer, td_sunat character varying, nro_comprobante character varying, debe numeric, haber numeric, saldomn numeric, saldome numeric, group_balance character varying, tc numeric) 
    LANGUAGE 'plpgsql'

    COST 100
    VOLATILE 
    ROWS 1000
AS $BODY$
BEGIN
	RETURN QUERY  
select b1.partner_id,
b1.account_id,
b1.td_sunat,
b1.nro_comprobante,
b1.debe,
b1.haber,
b1.saldomn,
b1.saldome,
b3.group_balance,
CASE
		WHEN b3.group_balance::text = ANY (ARRAY['B1'::character varying, 'B2'::character varying]::text[]) THEN ( SELECT edcl.compra
		   FROM exchange_diff_config_line edcl
			 LEFT JOIN exchange_diff_config edc ON edc.id = edcl.line_id
			 LEFT JOIN account_period ap ON ap.id = edcl.period_id
		  WHERE edc.company_id = $3 AND ap.code::text = $2::text)
		ELSE ( SELECT edcl.venta
		   FROM exchange_diff_config_line edcl
			 LEFT JOIN exchange_diff_config edc ON edc.id = edcl.line_id
			 LEFT JOIN account_period ap ON ap.id = edcl.period_id
		  WHERE edc.company_id = $3 AND ap.code::text = $2::text)
	END AS tc
from get_saldos_me_documento($1,$2,$3) b1
LEFT JOIN account_account b2 ON b2.id = b1.account_id
LEFT JOIN account_type_it b3 ON b3.id = b2.account_type_it_id;
END;
$BODY$;

----------------------------------------------------------------------------------------------------------------------------------------------------------
DROP FUNCTION IF EXISTS public.get_saldos_me_documento_final(character varying,character varying,integer) CASCADE;

CREATE OR REPLACE FUNCTION public.get_saldos_me_documento_final(
	fiscal_year character varying,
	periodo character varying,
	company_id integer)
    RETURNS TABLE(partner_id integer, account_id integer, td_sunat character varying, nro_comprobante character varying, debe numeric, haber numeric, saldomn numeric, saldome numeric, group_balance character varying, tc numeric, saldo_act numeric, diferencia numeric, difference_account_id integer) 
    LANGUAGE 'plpgsql'

    COST 100
    VOLATILE 
    ROWS 1000
AS $BODY$
BEGIN
	RETURN QUERY  
	SELECT *,
	round(coalesce(vst.tc,0) * vst.saldome,2) AS saldo_act,
	vst.saldomn - round(coalesce(vst.tc,0) * vst.saldome,2) AS diferencia,
	CASE 
	WHEN vst.saldomn < round(vst.tc * vst.saldome,2) AND vst.group_balance IN ('B1','B2') THEN (SELECT edc.profit_account_id FROM exchange_diff_config edc WHERE edc.company_id = $3)
	WHEN vst.saldomn > round(vst.tc * vst.saldome,2) AND vst.group_balance IN ('B1','B2') THEN (SELECT edc.loss_account_id FROM exchange_diff_config edc WHERE edc.company_id = $3)
	WHEN (-1 * vst.saldomn) > (-1 * round(vst.tc * vst.saldome,2)) AND vst.group_balance IN ('B3','B4','B5') THEN (SELECT edc.profit_account_id FROM exchange_diff_config edc WHERE edc.company_id = $3)
	WHEN (-1 * vst.saldomn) < (-1 * round(vst.tc * vst.saldome,2)) AND vst.group_balance IN ('B3','B4','B5') THEN (SELECT edc.loss_account_id FROM exchange_diff_config edc WHERE edc.company_id = $3) END AS difference_account_id
	FROM get_saldos_me_documento_2($1||'00',$2,$3) vst;
END;
$BODY$;
-------------------------------------------------------------------------------------------------------------------------------------------------------------
DROP FUNCTION IF EXISTS public.get_maturity_analysis(date, date, integer, character varying) CASCADE;

CREATE OR REPLACE FUNCTION public.get_maturity_analysis(
	first_date date,
	end_date date,
	company_id integer,
	type character varying)
    RETURNS TABLE(fecha_emi date, fecha_ven date, cuenta character varying, divisa character varying, tdp character varying, doc_partner character varying, partner character varying, td_sunat character varying, nro_comprobante character varying, saldo_mn numeric, saldo_me numeric, partner_id integer, cero_treinta numeric, treinta1_sesenta numeric, sesenta1_noventa numeric, noventa1_ciento20 numeric, ciento21_ciento50 numeric, ciento51_ciento80 numeric, ciento81_mas numeric) 
    LANGUAGE 'plpgsql'

    COST 100
    VOLATILE 
    ROWS 1000
AS $BODY$
BEGIN
	RETURN QUERY  
	select 
	b1.fecha_emi,
	b1.fecha_ven,
	b1.cuenta,
	b1.divisa,
	b1.tdp,
	b1.doc_partner,
	b1.partner,
	b1.td_sunat,
	b1.nro_comprobante,
	b1.saldo_mn,
	b1.saldo_me,
	b1.partner_id,
	case when b1.atraso between 0 and 30 then b1.saldo_mn else 0 end as cero_treinta,
	case when b1.atraso between 31 and 60 then b1.saldo_mn else 0 end as treinta1_sesenta,
	case when b1.atraso between 61 and 90 then b1.saldo_mn else 0 end as sesenta1_noventa,
	case when b1.atraso between 91 and 120 then b1.saldo_mn else 0 end as noventa1_ciento20,
	case when b1.atraso between 121 and 150 then b1.saldo_mn else 0 end as ciento21_ciento50,
	case when b1.atraso between 151 and 180 then b1.saldo_mn else 0 end as ciento51_ciento80,
	case when b1.atraso >180 then b1.saldo_mn else 0 end as ciento81_mas 
	from
	(
	select 
	case when a1.fecha_doc::date is null then a1.fecha_con::date else a1.fecha_doc::date end as fecha_emi,
	a1.fecha_ven as fecha_ven,
	a1.cuenta as cuenta,
	case when a3.name is not null then a3.name else 'PEN' end as divisa,
	a1.td_partner as tdp,
	a1.doc_partner as doc_partner,
	a1.partner,
	a1.td_sunat,
	a1.nro_comprobante,
	case when  a2.internal_type='receivable' then a1.saldo_mn else -a1.saldo_mn end as saldo_mn,
	case when  a2.internal_type='receivable' then a1.saldo_me else -a1.saldo_me end as saldo_me,
	case when a1.fecha_ven is not null then $2 - a1.fecha_ven else 0 end as atraso,
	a1.account_id,
	a2.internal_type,
	a1.partner_id
	from 
	get_saldos($1,$2,$3,'date') a1
	left join account_account a2 on a2.id=a1.account_id
	left join res_currency a3 on a3.id=a2.currency_id
	where a1.nro_comprobante is not null and a1.saldo_mn <> 0
	)b1
	where b1.internal_type = $4;
END;
$BODY$;