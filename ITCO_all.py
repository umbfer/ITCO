import numpy as np
import pandas as pd
import datetime
import dateparser
import warnings

#
# Script per il trattamento e l'analisi dei dati ITCO
# Umberto Ferraro Petrillo
# Ultima revisione: 24/12/24


# Input and output files

patients_path = "data/patient_21.10.csv"
surgeries_path = "data/surgery_21.10.csv"
visits_path = "data/visits_21.10.csv"


xls_output_file= 'output/output_short.xlsx'
csv_output_file= 'output/output_short.csv'

# Variabili configurazione

# Se diverso da None, processa unicamente il paziente di cui si fornisce l'id
# Esempio: utilizzando la seguente definizione la procedura sarà fatta girare
# per il solo paziente con id 1234
# filter_on_patient = 1234



filter_on_patient = False
patients_selection = ["1-1941"]


use_v2 = True

# Se True, valuta i criteri di inclusione/esclusione
perform_exclusion = True
# Se True, i pazienti escludibili sono inclusi comunque (con un set di attributi ridotti)
include_excluded_patients = False
# Se True, esclude i pazienti che non hanno alcuna surgery
skip_missing_surgery = False
# Se True, esclude i pazienti che non hanno alcuna visit
skip_missing_visit = False
# Se True, calcola la variabile ata_risk
eval_ata_risk = True
# Se True, abilita la stampa a scherma di messaggi diagnostici
debug = False

# Decide quale tipo di criteri adoperare (nota: il supporto per la modalità "siena" è stato rimosso)
mode="roma"

warnings.filterwarnings(
    "ignore",
    message="The localize method is no longer necessary, as this time zone supports the fold attribute",
)

def get_age(local_birth_date, reference_date):
    return reference_date.year - local_birth_date.year - ((reference_date.month, reference_date.day) < (local_birth_date.month, local_birth_date.day))




def get_month_diff(a, b):
    return abs(12 * (a.year - b.year) + (a.month - b.month))


debug_level = 1  # 0 = nessun output, 1 = base, 2 = dettagliato, 3 = verbose

def log_debug(message, level=1):
    if debug_level >= level:
        print(message)

def get_static_response_to_treatment1(v):
    visit_id = v.get('id')

    structural = v['ncifsuspiciouslympnode'] == 2 or v['imgsuspiciousneck'] == 2 or \
                 v['imgsuspiciousdistantmeta'] == 2 or v['raiuptake'] > 2

    biochemical = (
        (pd.isna(v['ncsuspiciouslympnodes']) or v['ncsuspiciouslympnodes'] == 1) and
        (v['ncsuspiciousresidualtissue'] == 1 or pd.isna(v['ncsuspiciousresidualtissue'])) and
        (pd.isna(v['imgsuspiciousdistantmeta']) or v['imgsuspiciousdistantmeta'] == 1) and
        (v['lb_basaltg'] >= 1 or v['lblstimulatedtg'] >= 10)
    )

    indeterminate = (
        v['ncifsuspiciouslympnode'] == 1 or
        v['raiuptake'] == 2 or
        (0.2 <= v['lb_basaltg'] < 1) or
        (1 <= v['lblstimulatedtg'] < 10) or
        v['lbtgab'] == 2
    )

    excellent = (
        (pd.isna(v['ncsuspiciouslympnodes']) or v['ncsuspiciouslympnodes'] == 1) and
        (v['ncsuspiciousresidualtissue'] == 1 or pd.isna(v['ncsuspiciousresidualtissue'])) and
        (pd.isna(v['imgsuspiciousdistantmeta']) or v['imgsuspiciousdistantmeta'] == 1) and
        v['lbtgab'] == 1 and
        (v['lb_basaltg'] < 0.2 or v['lblstimulatedtg'] < 1)
    )

    if structural:
        log_debug(f"[Visit ID: {visit_id}] Structural incomplete", level=3)
        return 2
    elif biochemical:
        log_debug(f"[Visit ID: {visit_id}] Biochemical incomplete", level=3)
        return 3
    elif indeterminate:
        log_debug(f"[Visit ID: {visit_id}] Indeterminate", level=3)
        return 1
    elif excellent:
        log_debug(f"[Visit ID: {visit_id}] Excellent", level=3)
        return 4

    log_debug(f"[Visit ID: {visit_id}] No category at all", level=3)
    return -1

def get_dynamic_response_to_treatment1(v):
    if pd.isna(v['prev_id']):
        return get_static_response_to_treatment1(v)

    visit_id = v.get('id')

    var_lbtgablevels = v['var_lbtgablevels']
    abs_lbtgablevels = v['abs_lbtgablevels']

    structural = v['ncifsuspiciouslympnode'] == 2 or v['imgsuspiciousneck'] == 2 or \
                 v['imgsuspiciousdistantmeta'] == 2 or v['raiuptake'] > 2

    biochemical = (
        (pd.isna(v['ncsuspiciouslympnodes']) or v['ncsuspiciouslympnodes'] == 1) and
        (v['ncsuspiciousresidualtissue'] == 1 or pd.isna(v['ncsuspiciousresidualtissue'])) and
        (pd.isna(v['imgsuspiciousdistantmeta']) or v['imgsuspiciousdistantmeta'] == 1) and
        (v['lb_basaltg'] >= 1 or v['lblstimulatedtg'] >= 10 or  (v['lbtgab'] == 2 and var_lbtgablevels > 20 and abs_lbtgablevels > 0.1))
    )

    indeterminate = (
        v['ncifsuspiciouslympnode'] == 1 or
        v['raiuptake'] == 2 or
        (0.2 <= v['lb_basaltg'] < 1) or
        (1 <= v['lblstimulatedtg'] < 10) or
        v['lbtgab'] == 2 or
        (v['lbtgab'] == 2 and var_lbtgablevels <= 20 and abs_lbtgablevels>0.1)
    )

    excellent = (
        (pd.isna(v['ncsuspiciouslympnodes']) or v['ncsuspiciouslympnodes'] == 1) and
        (v['imgsuspiciousneck'] == 1 or pd.isna(v['imgsuspiciousneck'])) and
        (pd.isna(v['imgsuspiciousdistantmeta']) or v['imgsuspiciousdistantmeta'] == 1) and
        v['lbtgab'] == 1 and
        (v['lb_basaltg'] < 0.2 or v['lblstimulatedtg'] < 1)
    )

    if structural:
        log_debug(f"[Visit ID: {visit_id}] Structural incomplete", level=3)
        return 2
    elif biochemical:
        log_debug(f"[Visit ID: {visit_id}] Biochemical incomplete", level=3)
        return 3
    elif indeterminate:
        log_debug(f"[Visit ID: {visit_id}] Indeterminate", level=3)
        return 1
    elif excellent:
        log_debug(f"[Visit ID: {visit_id}] Excellent", level=3)
        return 4

    log_debug(f"[Visit ID: {visit_id}] No category at all", level=3)
    return -1

def get_static_response_to_treatment2(v):
    visit_id = v.get('id')

    structural = (
        v['ncifsuspiciouslympnode'] == 2 or
        v['imgsuspiciousneck'] == 2 or
        v['imgsuspiciousdistantmeta'] == 2 or
        v['raiuptake'] > 2
    )

    biochemical = (
        (pd.isna(v['ncsuspiciouslympnodes']) or v['ncsuspiciouslympnodes'] == 1) and
        (v['ncsuspiciousresidualtissue'] == 1 or pd.isna(v['ncsuspiciousresidualtissue'])) and
        (pd.isna(v['imgsuspiciousdistantmeta']) or v['imgsuspiciousdistantmeta'] == 1) and
        (v['lb_basaltg'] >= 5)
    )

    indeterminate = (
        (v['ncifsuspiciouslympnode'] == 1) or
        v['raiuptake'] == 2 or
        (0.2 <= v['lb_basaltg'] < 5) or
        (2 <= v['lblstimulatedtg'] < 10) or
        v['lbtgab'] == 2
    )

    excellent = (
        (pd.isna(v['ncsuspiciouslympnodes']) or v['ncsuspiciouslympnodes'] == 1) and
        (v['ncsuspiciousresidualtissue'] == 1 or pd.isna(v['ncsuspiciousresidualtissue'])) and
        (pd.isna(v['imgsuspiciousdistantmeta']) or v['imgsuspiciousdistantmeta'] == 1) and
        v['lbtgab'] == 1 and
        (v['lb_basaltg'] < 0.2 or v['lblstimulatedtg'] < 2)
    )

    if structural:
        log_debug(f"[Visit ID: {visit_id}] Structural incomplete", level=3)
        return 2
    elif biochemical:
        log_debug(f"[Visit ID: {visit_id}] Biochemical incomplete", level=3)
        return 3
    elif indeterminate:
        log_debug(f"[Visit ID: {visit_id}] Indeterminate", level=3)
        return 1
    elif excellent:
        log_debug(f"[Visit ID: {visit_id}] Excellent", level=3)
        return 4

    log_debug(f"[Visit ID: {visit_id}] No category at all", level=3)
    return -1

def get_dynamic_response_to_treatment2(v):
    if pd.isna(v['prev_id']):
        return get_static_response_to_treatment2(v)

    visit_id = v.get('id')

    var_lbtgablevels = v['var_lbtgablevels']
    var_lb_basaltg = v['var_lb_basaltg']
    abs_lbtgablevels = v['abs_lbtgablevels']
    abs_lb_basaltg = v['abs_lb_basaltg']


    structural = (
        v['ncifsuspiciouslympnode'] == 2 or
        v['imgsuspiciousneck'] == 2 or
        v['imgsuspiciousdistantmeta'] == 2 or
        v['raiuptake'] > 2
    )

    biochemical = (
        (pd.isna(v['ncsuspiciouslympnodes']) or v['ncsuspiciouslympnodes'] == 1) and
        (v['ncsuspiciousresidualtissue'] == 1 or pd.isna(v['ncsuspiciousresidualtissue'])) and
        (pd.isna(v['imgsuspiciousdistantmeta']) or v['imgsuspiciousdistantmeta'] == 1) and
        (v['lb_basaltg'] >= 5) or (v['lbtgab'] == 2 and var_lbtgablevels > 20 and abs_lbtgablevels > 0.1) or (var_lb_basaltg > 20 and v['lb_basaltg'] > 1 and abs_lb_basaltg > 0.1)
    )

    indeterminate = (
        (v['ncifsuspiciouslympnode'] == 1) or
        v['raiuptake'] == 2 or
        (0.2 <= v['lb_basaltg'] < 5) or
        (2 <= v['lblstimulatedtg'] <= 10) or
        (v['lbtgab'] == 2 and
        var_lbtgablevels <= 20 and abs_lbtgablevels>0.1)
    )

    excellent = (
        (pd.isna(v['ncsuspiciouslympnodes']) or v['ncsuspiciouslympnodes'] == 1) and
        (v['ncsuspiciousresidualtissue'] == 1 or pd.isna(v['imgsuspiciousneck'])) and
        (pd.isna(v['imgsuspiciousdistantmeta']) or v['imgsuspiciousdistantmeta'] == 1) and
        v['lbtgab'] == 1 and
        (v['lb_basaltg'] < 0.2 or v['lblstimulatedtg'] < 2)
    )

    if structural:
        log_debug(f"[Visit ID: {visit_id}] Structural incomplete", level=3)
        return 2
    elif biochemical:
        log_debug(f"[Visit ID: {visit_id}] Biochemical incomplete", level=3)
        return 3
    elif indeterminate:
        log_debug(f"[Visit ID: {visit_id}] Indeterminate", level=3)
        return 1
    elif excellent:
        log_debug(f"[Visit ID: {visit_id}] Excellent", level=3)
        return 4

    log_debug(f"[Visit ID: {visit_id}] No category at all", level=3)
    return -1

def get_static_response_to_treatment3(v):
    visit_id = v.get('id')

    structural = (
        v['ncifsuspiciouslympnode'] == 2 or
        v['imgsuspiciousneck'] == 2 or
        v['imgsuspiciousdistantmeta'] == 2 or
        v['raiuptake'] > 2
    )

    biochemical = (
        (v['ncsuspiciouslympnodes'] == 1) and
        (v['ncsuspiciousresidualtissue'] == 1) and
        ((v['imgsuspiciousdistantmeta'] == 1)  or pd.isna(v['imgsuspiciousdistantmeta']))
    )

    indeterminate = (
         v['ncifsuspiciouslympnode'] == 1
    )

    excellent = (
        (v['ncsuspiciouslympnodes'] == 1) and
        (v['ncsuspiciousresidualtissue'] == 1 ) and
        (v['imgsuspiciousdistantmeta'] == 1) and
        v['lbtgab'] == 1 and
        v['dsevidence'] == 1
    )

    if structural:
        log_debug(f"[Visit ID: {visit_id}] Structural incomplete", level=3)
        return 2
    elif biochemical:
        log_debug(f"[Visit ID: {visit_id}] Biochemical incomplete", level=3)
        return 3
    elif indeterminate:
        log_debug(f"[Visit ID: {visit_id}] Indeterminate", level=3)
        return 1
    elif excellent:
        log_debug(f"[Visit ID: {visit_id}] Excellent", level=3)
        return 4

    log_debug(f"[Visit ID: {visit_id}] No category at all", level=3)
    return -1

def get_dynamic_response_to_treatment3(v):
    if pd.isna(v['prev_id']):
        return get_static_response_to_treatment3(v)

    visit_id = v.get('id')

    var_lbtgablevels = v['var_lbtgablevels']
    var_lb_basaltg = v['var_lb_basaltg']
    abs_lbtgablevels = v['abs_lbtgablevels']
    abs_lb_basaltg = v['abs_lb_basaltg']


    structural = (
            v['ncifsuspiciouslympnode'] == 2 or
            v['imgsuspiciousneck'] == 2 or
            v['imgsuspiciousdistantmeta'] == 2 or
            v['raiuptake'] > 2
    )

    biochemical = (
            v['ncsuspiciouslympnodes'] == 1 and
            v['ncsuspiciousresidualtissue'] == 1 and
            (v['imgsuspiciousdistantmeta'] == 1 or (pd.isna(v['imgsuspiciousdistantmeta'])))and
            (
                    (v['lbtgab'] == 2 and var_lbtgablevels > 20 and abs_lbtgablevels > 0.1) or
                    (var_lb_basaltg > 20 and v['lb_basaltg'] > 10 and abs_lb_basaltg > 0.1)
            )
    )

    indeterminate = (
            v['ncsuspiciouslympnodes'] == 1
    )

    excellent = (
            ( v['ncsuspiciouslympnodes'] == 1) and
            (v['ncsuspiciousresidualtissue'] == 1 ) and
            ((v['imgsuspiciousdistantmeta'] == 1) or (pd.isna(v['imgsuspiciousdistantmeta']))) and
            v['lbtgab'] == 1 and
            v['dsevidence'] == 1
    )

    if structural:
        log_debug(f"[Visit ID: {visit_id}] Structural incomplete", level=3)
        return 2
    elif biochemical:
        log_debug(f"[Visit ID: {visit_id}] Biochemical incomplete", level=3)
        return 3
    elif indeterminate:
        log_debug(f"[Visit ID: {visit_id}] Indeterminate", level=3)
        return 1
    elif excellent:
        log_debug(f"[Visit ID: {visit_id}] Excellent", level=3)
        return 4

    log_debug(f"[Visit ID: {visit_id}] No category at all", level=3)
    return -1

def determine_treatment(p, s):
    dt_init = p["dt_initial_treatment"]
    rra_date = p["rradate"]

    if pd.isna(dt_init):
        return 0

    if dt_init == rra_date:
        return 1

    if s is not None and not s.empty:
        matching_surgery = s[s["sgdateofsurgery"] == dt_init]

        if not matching_surgery.empty:
            approach = matching_surgery["sgapproach"].iloc[0]

            if pd.isna(approach):
                return np.nan
            elif approach in [1, 2]:
                return 2
            elif approach == 3:
                # Controlla se esiste un solo approccio chirurgico valido per il paziente
                patient_approaches = s["sgapproach"].dropna()
                if len(patient_approaches) == 1:
                    return 3
                else:
                    return 0
            else:
                return 0
        else:
            # dt_initial_treatment <> sgdateofsurgery
            return 0

    return 0

# NOTA: la procedura lavora su una copia di visits dal momento che apporta delle modifiche permanenti,
# eliminando le visite di volta in volta escluse.
# Tra le informazioni restituite, vi è l'indicazione della data della visita presa come riferimento

def get_new_rtt(reference_date, visits, s, p, mode):
    global first_exclusion_vis_3

    rtt_old = -2
    rtt_new = -2

    treatment = determine_treatment(p, s) if not s.empty else 0

    if pd.isna(reference_date) or visits.empty:
        return (rtt_old, rtt_new, treatment, None)

    p = p.squeeze()

    while not visits.empty:
        # Individuo la visita più vicina alla reference date
        closest_date = min(visits['date'], key=lambda x: abs(x - reference_date))

        # Individuo l'ultima visita precedente three_years_closest, se esistente. Altrimenti, None
        earlier_visits = visits[visits['date'] < closest_date]

        log_debug('reference date (RTT): ' + str(reference_date),2)
        log_debug('closest date (RTT): ' + str(closest_date),2)

        if get_month_diff(closest_date, reference_date) > 6:
            closest_date = None
            break

        # Se la visita individuata rientra nel range di date ammissibili, procedo
        v = visits[visits['date'] == closest_date]
        v = v.loc[v['id'].idxmax()]

        # Se la visita non e' stata esclusa per qualche motivo, calcolo rtt
        if v['id'] not in excluded_visit:
#                print(f'visit {v['id']}')
            if s['sgapproach'].isna().all():
                first_exclusion_vis_3[p['id']] = 1
            # TT+RRA
            elif treatment==1:
                rtt_old = get_static_response_to_treatment1(v)
                rtt_new = get_dynamic_response_to_treatment1(v)
            # TT alone
            elif treatment==2:
                rtt_old = get_static_response_to_treatment2(v)
                rtt_new = get_dynamic_response_to_treatment2(v)
            # Lobectomy
            elif treatment==3:
                rtt_old = get_static_response_to_treatment3(v)
                rtt_new = get_dynamic_response_to_treatment3(v)

            else:
                first_exclusion_vis_3[p['id']] = 1
            break
        else:
            # Escludo la visita precedentemente individuata, e considero la successiva in ordine di distanza
            # dalla data di riferimento
            first_exclusion_vis_2[p['id']] = 1
            visits = visits[visits['date'] != closest_date]
            closest_date = None
    else:
        first_exclusion_vis_3[p['id']]=3

    return (rtt_old, rtt_new, treatment, closest_date)

def get_new_rtt_latest(visits, s, p, mode):
    global first_exclusion_vis_3

    rtt_old = -2
    rtt_new = -2

    treatment = determine_treatment(p, s) if not s.empty else 0

    if visits.empty:
        return (rtt_old, rtt_new, treatment)

    p = p.squeeze()

    while not visits.empty:

        # Individuo la visita più vicina alla reference date
        closest_date = max(visits['date'])
        v = visits[visits['date'] == closest_date]
        v = v.loc[v['id'].idxmax()]

        # Individuo l'ultima visita precedente , se esistente. Altrimenti, None
        # necessario per il supporto dei criteri di Siena

        earlier_visits = visits[visits['date'] < closest_date]

        if len(earlier_visits.index) > 0:
            closest_date_prev = min(earlier_visits['date'], key=lambda x: abs(x - closest_date))
            prev_v = visits[visits['date'] == closest_date_prev]
            prev_v = prev_v.loc[prev_v['id'].idxmax()]

        else:
            prev_v = None

        log_debug('closest date (RTT): ' + str(closest_date),2)

        # Se la visita individuata rientra nel range di date ammissibili, procedo
        v = visits[visits['date'] == closest_date]
        v = v.loc[v['id'].idxmax()]

        # Se la visita non e' stata esclusa per qualche motivo, calcolo rtt
        if v['id'] not in excluded_visit:
            if treatment==1:
                rtt_old = get_static_response_to_treatment1(v)
                rtt_new = get_dynamic_response_to_treatment1(v)
            # TT alone
            elif treatment==2:
                rtt_old = get_static_response_to_treatment2(v)
                rtt_new = get_dynamic_response_to_treatment2(v)
            # Lobectomy
            elif treatment==3:
                rtt_old = get_static_response_to_treatment3(v)
                rtt_new = get_dynamic_response_to_treatment3(v)
            else:
                first_exclusion_vis_3[p['id']] = 1
            break
        else:
            # Escludo la visita precedentemente individuata, e considero la successiva in ordine di distanza
            # dalla data di riferimento
            first_exclusion_vis_2[p['id']] = 1
            visits = visits[visits['date'] != closest_date]
    else:
        first_exclusion_vis_3[p['id']]=3


    return (rtt_old,rtt_new, treatment)



def get_all_rtt_for_patient(visits, s, p, mode):
    rtt_all = []

    if s['sgapproach'].isna().all():
        return rtt_all

    for i, v in visits.iterrows():
        if v['id'] in excluded_visit:
            continue

        reference_date = v['date']
        treatment = determine_treatment(p, s) if not s.empty else 0

        if treatment == 1:
            rtt = get_dynamic_response_to_treatment1(v)
        elif treatment == 2:
            rtt = get_dynamic_response_to_treatment2(v)
        elif treatment == 3:
            rtt = get_dynamic_response_to_treatment3(v)
        else:
            rtt = -2  # trattamento non determinato

        rtt_all.append((int(v['id']), reference_date.strftime('%Y-%m-%d'), int(rtt) if pd.notna(rtt) else -1))

    return rtt_all


def load_patients_v1(patients_path):
    p=pd.read_csv(patients_path, sep="\t",low_memory=False, decimal=".",thousands=",")
    new_patient=p.iloc[:,
                [0, 61, 4, 63, 64, 65, 0, 10, 1, 6, 26, 25, 32, 33, 39, 30, 35, 34, 36, 0, 74, 75, 28, 29, 31]]
    new_patient.columns=["id", "rra", "sex", "rradate", "rraradioiodineactivity", "rraradioiodineactivitynum",
                         "prophylacticcentralneckdissection", "tcddiagnosis", "birthdate",
                         "clinicalcentre_id", "hihistologicsubtypes", "hicancertype", "hivascolarinvasion",
                         "hilymphnodemetastasis",
                         "hysurgicalmargins", "hiextraextension", "hilymphnodemetastasisnum",
                         "hinumberofremovedlymphnodes",
                         "hylympnodesize", "surgery_count", "satoptm", "forcedm", "hitumorsize", "hitumoralfoci",
                         "invasionofstrapmuscles"]

    # We drop from the Dataframe all duplicated header lines (if any) plus all empty lines
    new_patient = new_patient.drop(new_patient[new_patient['birthdate'] == 'Date of birth'].index)
    new_patient = new_patient[pd.to_numeric(new_patient['id'], errors='coerce').notnull()]

    new_patient.id=pd.to_numeric(new_patient.id)

    if filter_on_patient:
        new_patient = new_patient[new_patient['id'] == filter_on_patient]


    new_patient.rradate.fillna('',inplace=True)
    new_patient.birthdate.fillna('',inplace=True)

    new_patient.rradate =new_patient.rradate.apply(lambda x: dateparser.parse(x, languages=['it']))
    new_patient.birthdate =new_patient.birthdate.apply(lambda x: dateparser.parse(x, languages=['it']))

#    new_patient=new_patient.fillna(
#        {'hilymphnodemetastasisnum': 0, 'hilymphnodemetastasis': 0, 'hiextraextension': 0, 'hylympnodesize': 0,
#         'rra': 0})

    new_patient.rra = pd.to_numeric(new_patient.rra, downcast='integer')
    new_patient.sex = pd.to_numeric(new_patient.sex, downcast='integer')
    new_patient.rraradioiodineactivity = pd.to_numeric(new_patient.rraradioiodineactivity, downcast='integer')
    new_patient.rraradioiodineactivitynum = pd.to_numeric(new_patient.rraradioiodineactivitynum)
    new_patient.prophylacticcentralneckdissection = pd.to_numeric(new_patient.prophylacticcentralneckdissection, downcast='integer')
    new_patient.tcddiagnosis = pd.to_numeric(new_patient.tcddiagnosis, downcast='integer')
    new_patient.clinicalcentre_id = pd.to_numeric(new_patient.clinicalcentre_id, downcast='integer')
    new_patient.hihistologicsubtypes = pd.to_numeric(new_patient.hihistologicsubtypes, downcast='integer')
    new_patient.hicancertype = pd.to_numeric(new_patient.hicancertype, downcast='integer')
    new_patient.hivascolarinvasion = pd.to_numeric(new_patient.hivascolarinvasion, downcast='integer')
    new_patient.hilymphnodemetastasis = pd.to_numeric(new_patient.hilymphnodemetastasis, downcast='integer')
    new_patient.hysurgicalmargins = pd.to_numeric(new_patient.hysurgicalmargins, downcast='integer')
    new_patient.hiextraextension = pd.to_numeric(new_patient.hiextraextension, downcast='integer')
    new_patient.hilymphnodemetastasisnum = pd.to_numeric(new_patient.hilymphnodemetastasisnum, downcast='integer')
    new_patient.hinumberofremovedlymphnodes = pd.to_numeric(new_patient.hinumberofremovedlymphnodes, downcast='integer')
    new_patient.hylympnodesize = pd.to_numeric(new_patient.hylympnodesize, downcast='integer')
    new_patient.surgery_count = pd.to_numeric(new_patient.surgery_count, downcast='integer')
    new_patient.satoptm = pd.to_numeric(new_patient.satoptm, downcast='integer')
    new_patient.forcedm = pd.to_numeric(new_patient.forcedm, downcast='integer')
    new_patient.hitumorsize = pd.to_numeric(new_patient.hitumorsize)
    new_patient.hitumoralfoci = pd.to_numeric(new_patient.hitumoralfoci, downcast='integer')
    new_patient.invasionofstrapmuscles = pd.to_numeric(new_patient.invasionofstrapmuscles, downcast='integer')

    new_patient.id =pd.to_numeric(new_patient.id, downcast='integer')

    print(f"Overall number of patients: {len(new_patient.index)}")
    return new_patient

def load_patients_v2(patients_path):
   # p=pd.read_csv(patients_path, sep="\t",low_memory=False, decimal=".",thousands=",")

    df = pd.read_csv(patients_path, sep=",", decimal=".", thousands=",", na_values="NA", low_memory=False)


    if filter_on_patient:
        df = df[df['record_id'].isin(patients_selection)]

    # Rinomina le colonne per farle combaciare con il vecchio schema
    # Ad esempio: record_id -> id
    rename_map = {
        "record_id": "id"
    }

    df.rename(columns=rename_map, inplace=True)

    df["birthdate"] = pd.NaT



    df["age"] = df["age"].fillna(-1)

    df["forcedm"] = 0

    # Il numero di surgeries per paziente è al momento fissato ad 1
    df["surgery_count"] = 1

    # Ora selezioni solo le colonne che ti servivano nella vecchia “patient”
    new_patient = df[[
        "id", "rra", "sex", "rradate", "rraradioiodineactivity",
        #"rraradioiodineactivitynum", "prophylacticcentralneckdissection",
        "rraradioiodineactivitynum",
        "tcddiagnosis", "birthdate", "age","clinicalcentre_id",
        "hihistologicsubtypes", "hicancertype", "hivascolarinvasion",
        "hilymphnodemetastasis", "hysurgicalmargins", "hiextraextension",
        "hilymphnodemetastasisnum", "hinumberofremovedlymphnodes",
        "hylympnodesize", "satoptm", "forcedm", "hitumorsize",
        "hitumoralfoci", "invasionofstrapmuscles","surgery_count", "atarisk",
        "dt_initial_treatment", "initial_treatment_complete"
    ]].copy()


    new_patient.rename(columns={"atarisk": "external_ata_risk"}, inplace=True)

# new_patient=p.iloc[:,
    #             [0, 61, 4, 63, 64, 65, 0, 10, 1, 6, 26, 25, 32, 33, 39, 30, 35, 34, 36, 0, 74, 75, 28, 29, 31]]
    # new_patient.columns=["id", "rra", "sex", "rradate", "rraradioiodineactivity", "rraradioiodineactivitynum",
    #                      "prophylacticcentralneckdissection", "tcddiagnosis", "birthdate",
    #                      "clinicalcentre_id", "hihistologicsubtypes", "hicancertype", "hivascolarinvasion",
    #                      "hilymphnodemetastasis",
    #                      "hysurgicalmargins", "hiextraextension", "hilymphnodemetastasisnum",
    #                      "hinumberofremovedlymphnodes",
    #                      "hylympnodesize", "surgery_count", "satoptm", "forcedm", "hitumorsize", "hitumoralfoci",
    #                      "invasionofstrapmuscles"]

    # We drop from the Dataframe all duplicated header lines (if any) plus all empty lines
    new_patient = new_patient.drop(new_patient[new_patient['birthdate'] == 'Date of birth'].index)
    # new_patient = new_patient[pd.to_numeric(new_patient['id'], errors='coerce').notnull()]



#    new_patient.id=pd.to_numeric(new_patient.id)


    if filter_on_patient:
        new_patient = new_patient[new_patient['id'].isin(patients_selection)]

    #new_patient.rradate.fillna('',inplace=True)
    #new_patient.birthdate.fillna('',inplace=True)


    new_patient.rradate = new_patient.rradate.fillna('')
    new_patient.birthdate = new_patient.birthdate.fillna('')

#   nel formato v2 le date sono nella forma US
#   new_patient.rradate =new_patient.rradate.apply(lambda x: dateparser.parse(x, languages=['it']))
#   new_patient.birthdate =new_patient.birthdate.apply(lambda x: dateparser.parse(x, languages=['it']))
# new_patient.rradate = new_patient.rradate.apply(lambda x: dateparser.parse(x))

    new_patient["rradate"] = pd.to_datetime(new_patient["rradate"], format="%Y-%m-%d", errors="coerce")
    new_patient["dt_initial_treatment"] = pd.to_datetime(new_patient["dt_initial_treatment"], format="%Y-%m-%d", errors="coerce")


#    new_patient=new_patient.fillna(
#        {'hilymphnodemetastasisnum': 0, 'hilymphnodemetastasis': 0, 'hiextraextension': 0, 'hylympnodesize': 0,
#         'rra': 0})

    new_patient.rra = pd.to_numeric(new_patient.rra, downcast='integer')
    new_patient.sex = pd.to_numeric(new_patient.sex, downcast='integer')
    new_patient.rraradioiodineactivity = pd.to_numeric(new_patient.rraradioiodineactivity, downcast='integer')
    new_patient.rraradioiodineactivitynum = pd.to_numeric(new_patient.rraradioiodineactivitynum)
#    new_patient.prophylacticcentralneckdissection = pd.to_numeric(new_patient.prophylacticcentralneckdissection, downcast='integer')
    new_patient.tcddiagnosis = pd.to_numeric(new_patient.tcddiagnosis, downcast='integer')
    new_patient.clinicalcentre_id = pd.to_numeric(new_patient.clinicalcentre_id, downcast='integer')
    new_patient.hihistologicsubtypes = pd.to_numeric(new_patient.hihistologicsubtypes, downcast='integer')
    new_patient.hicancertype = pd.to_numeric(new_patient.hicancertype, downcast='integer')
    new_patient.hivascolarinvasion = pd.to_numeric(new_patient.hivascolarinvasion, downcast='integer')
    new_patient.hilymphnodemetastasis = pd.to_numeric(new_patient.hilymphnodemetastasis, downcast='integer')
    new_patient.hysurgicalmargins = pd.to_numeric(new_patient.hysurgicalmargins, downcast='integer')
    new_patient.hiextraextension = pd.to_numeric(new_patient.hiextraextension, downcast='integer')
    new_patient.hilymphnodemetastasisnum = pd.to_numeric(new_patient.hilymphnodemetastasisnum, downcast='integer')
    new_patient.hinumberofremovedlymphnodes = pd.to_numeric(new_patient.hinumberofremovedlymphnodes, downcast='integer')
    new_patient.hylympnodesize = pd.to_numeric(new_patient.hylympnodesize, downcast='integer')
    new_patient.surgery_count = pd.to_numeric(new_patient.surgery_count, downcast='integer')
    new_patient.satoptm = pd.to_numeric(new_patient.satoptm, downcast='integer')
    new_patient.forcedm = pd.to_numeric(new_patient.forcedm, downcast='integer')
    new_patient.hitumorsize = pd.to_numeric(new_patient.hitumorsize)
    new_patient.hitumoralfoci = pd.to_numeric(new_patient.hitumoralfoci, downcast='integer')
    new_patient.invasionofstrapmuscles = pd.to_numeric(new_patient.invasionofstrapmuscles, downcast='integer')

    #new_patient.id =pd.to_numeric(new_patient.id, downcast='integer')
    new_patient.age = pd.to_numeric(new_patient.age, downcast='integer')


    print(f"Overall number of patients: {len(new_patient.index)}")
    return new_patient

def load_surgery_v1(surgeries_path):
    s=pd.read_csv(surgeries_path, sep="\t", decimal=".",thousands=",")
    new_surgery=s.iloc[:, [1, 0, 2, 3, 4, 5, 8]]
    new_surgery.columns=["id", "patient_id", "sgdateofsurgery", "sgapproach", "sgcentralcompartmentneckdissection",
                         "sglateralcompartmentneckdissection", "prophylacticcentralneckdissection"]

    new_surgery = new_surgery.drop(new_surgery[new_surgery['patient_id'] == 'Patient_id'].index)
    new_surgery=new_surgery[pd.to_numeric(new_surgery['id'], errors='coerce').notnull()]
    new_surgery.patient_id = pd.to_numeric(new_surgery.patient_id)

    if filter_on_patient:
        new_surgery = new_surgery[new_surgery['patient_id'].isin(patients_selection)]

    new_surgery.id=pd.to_numeric(new_surgery.id, downcast='integer')

    # we replace missing values with 0 for all variables except [Laboratory Basal Tg (ng/mL)] AND [Laboratory Stimulated Tg (ng/mL)]
    new_surgery=new_surgery.fillna({'prophylacticcentralneckdissection': 0})
    new_surgery.prophylacticcentralneckdissection=pd.to_numeric(new_surgery.prophylacticcentralneckdissection)
    new_surgery.sgapproach=pd.to_numeric(new_surgery.sgapproach)
    new_surgery.sgcentralcompartmentneckdissection=pd.to_numeric(new_surgery.sgcentralcompartmentneckdissection)
    new_surgery.sglateralcompartmentneckdissection=pd.to_numeric(new_surgery.sglateralcompartmentneckdissection)
    new_surgery.sgdateofsurgery =new_surgery.sgdateofsurgery.apply(lambda x: dateparser.parse(x, languages=['it']))

    print(f"Overall number of surgeries: {len(new_surgery.index)} ")
    return  new_surgery

def load_surgery_v2(surgeries_path):
    #s=pd.read_csv(surgeries_path, sep="\t", decimal=".",thousands=",")
    df = pd.read_csv(surgeries_path, sep=",", decimal=".", thousands=",", low_memory=False)

    rename_map = {
        "record_id": "patient_id"
    }
    df.rename(columns=rename_map, inplace=True)

 #    df = df[df["sgdateofsurgery"].notnull()].copy()

    df = df.dropna(subset=['sgdateofsurgery'])

    #  temporaneo: uso un id artificiale per ogni surgery
    df["id"] = pd.RangeIndex(start=1, stop=len(df) + 1)

    new_surgery = df[[
        "id", "patient_id", "sgdateofsurgery", "sgapproach",
        "sgcentralcompartmentneckdissection", "sglateralcompartmentneckdissection",
        "prophylacticcentralneckdissection"
    ]].copy()

    # new_surgery=s.iloc[:, [1, 0, 2, 3, 4, 5, 8]]
    # new_surgery.columns=["id", "patient_id", "sgdateofsurgery", "sgapproach", "sgcentralcompartmentneckdissection",
    #                      "sglateralcompartmentneckdissection", "prophylacticcentralneckdissection"]

    new_surgery = new_surgery.drop(new_surgery[new_surgery['patient_id'] == 'Patient_id'].index)
   # new_surgery=new_surgery[pd.to_numeric(new_surgery['id'], errors='coerce').notnull()]
   # new_surgery.patient_id = pd.to_numeric(new_surgery.patient_id)

    if filter_on_patient:
        new_surgery = new_surgery[new_surgery['patient_id'].isin(patients_selection)]

    #new_surgery.id=pd.to_numeric(new_surgery.id, downcast='integer')

    # we replace missing values with 0 for all variables except [Laboratory Basal Tg (ng/mL)] AND [Laboratory Stimulated Tg (ng/mL)]
    # new_surgery=new_surgery.fillna({'prophylacticcentralneckdissection': 0})
    new_surgery.prophylacticcentralneckdissection=pd.to_numeric(new_surgery.prophylacticcentralneckdissection)
    new_surgery.sgapproach=pd.to_numeric(new_surgery.sgapproach)
    new_surgery.sgcentralcompartmentneckdissection=pd.to_numeric(new_surgery.sgcentralcompartmentneckdissection)
    new_surgery.sglateralcompartmentneckdissection=pd.to_numeric(new_surgery.sglateralcompartmentneckdissection)
    #new_surgery.sgdateofsurgery =new_surgery.sgdateofsurgery.apply(lambda x: dateparser.parse(x))
    #new_surgery.sgdateofsurgery =new_surgery.sgdateofsurgery.apply(lambda x: dateparser.parse(x, languages=['it']))
    new_surgery["sgdateofsurgery"] = pd.to_datetime(new_surgery["sgdateofsurgery"], format="%Y-%m-%d", errors="coerce")

    print(f"Overall number of surgeries: {len(new_surgery.index)} ")
    return  new_surgery

def load_visits_v1(visits_path):
    v=pd.read_csv(visits_path, sep="\t", skiprows=1, decimal=".",thousands=",")
    new_visit=v.iloc[:, [1, 0, 2, 13, 14, 15, 16, 26, 27, 29, 21, 11, 6, 7, 12, 33, 43, 47, 50]]
    new_visit.columns=["id", "patient_id", "date", "ncnormalresidualtissue", "ncsuspiciousresidualtissue",
                       "ncsuspiciouslympnodes",
                       "ncifsuspiciouslympnode", "imgsuspiciousneck", "imgsuspiciousdistantmeta",
                       "dsevidence", "raiuptake", "lbtgab", "lb_basaltg", "lblstimulatedtg", "lbtgablevels", "trrai",
                       "trsurgery", "trexternalradio", "trother"]

    new_visit["id"] = range(1, len(new_visit) + 1)

    new_visit = new_visit.drop(new_visit[new_visit['patient_id'] == 'Patient_id'].index)
    new_visit=new_visit[pd.to_numeric(new_visit['id'], errors='coerce').notnull()]

    new_visit.patient_id = pd.to_numeric(new_visit.patient_id)

    if filter_on_patient:
        new_visit = new_visit[new_visit['patient_id'].isin(patients_selection)]

#    new_visit.date =new_visit.date.apply(lambda x: dateparser.parse(x, languages=['it']))
    new_visit["date"] = pd.to_datetime(new_visit["date"], format="%Y-%m-%d", errors="coerce")

    new_visit['trrai'].replace({1: 0, 2: 1}, regex=True, inplace=True)
    new_visit['trsurgery'].replace({1: 0, 2: 1}, regex=True, inplace=True)
    new_visit['trexternalradio'].replace({1: 0, 2: 1}, regex=True, inplace=True)
    new_visit['trother'].replace({1: 0, 2: 1}, regex=True, inplace=True)
    # NaN are automatically converted to NaT, by means of errors=coerce
#    new_visit['date']=pd.to_datetime(new_visit['date'],errors='coerce')
#    new_visit=new_visit.fillna(
#        { 'imgsuspiciousdistantmeta': 0, 'dsevidence': 0,
#         'raiuptake': 0, 'lbtgab': 0, 'lb_basaltg': 0, 'lbtgablevels': 0})


    new_visit.ncnormalresidualtissue = pd.to_numeric(new_visit.ncnormalresidualtissue, downcast='integer')
    new_visit.ncsuspiciousresidualtissue = pd.to_numeric(new_visit.ncsuspiciousresidualtissue, downcast='integer')
    new_visit.ncsuspiciouslympnodes = pd.to_numeric(new_visit.ncsuspiciouslympnodes, downcast='integer')
#    new_visit.ncifsuspiciouslympnodespresent = pd.to_numeric(new_visit.ncifsuspiciouslympnodespresent, downcast='integer')
    new_visit.imgsuspiciousneck = pd.to_numeric(new_visit.imgsuspiciousneck, downcast='integer')
    new_visit.imgsuspiciousdistantmeta = pd.to_numeric(new_visit.imgsuspiciousdistantmeta, downcast='integer')
    new_visit.dsevidence = pd.to_numeric(new_visit.dsevidence, downcast='integer')
    new_visit.raiuptake = pd.to_numeric(new_visit.raiuptake, downcast='integer')
    new_visit.lbtgab = pd.to_numeric(new_visit.lbtgab, downcast='integer')
    new_visit.lb_basaltg = pd.to_numeric(new_visit.lb_basaltg)
    new_visit.lblstimulatedtg = pd.to_numeric(new_visit.lblstimulatedtg)
    new_visit.lbtgablevels = pd.to_numeric(new_visit.lbtgablevels)
    new_visit.trrai = pd.to_numeric(new_visit.trrai, downcast='integer')
    new_visit.trsurgery = pd.to_numeric(new_visit.trsurgery, downcast='integer')
    new_visit.trexternalradio = pd.to_numeric(new_visit.trexternalradio, downcast='integer')

    print(f"Overall number of visits: {len(new_visit.index)} ")
    return new_visit

def load_visits_v2(visits_path):
    dtype_map = {
        "record_id": "string",
        "visit_id": "string",
        "visit_date": "string",
    }


    v = pd.read_csv(visits_path, sep=",", skiprows=0, decimal=".", thousands=",", dtype=dtype_map, low_memory=False)

    rename_map = {
        "record_id": "patient_id",
        "visit_id":"id",
        "visit_date": "date"
        # Attenzione a ncsuspiciouslympnode -> "ncifsuspiciouslympnodespresent"
#            "ncifsuspiciouslympnode": "ncifsuspiciouslympnodespresent",
    }

    v["trother"] = 0
    v.rename(columns=rename_map, inplace=True)

    # Temporaneamente tratto le date 1920-01-01 come na
    #v['date'] = v['date'].replace('1920-01-01', pd.NA)
    #v.dropna(subset=['date'], inplace=True)

    v["date"] = pd.to_datetime(v["date"].replace("1920-01-01", pd.NA), errors="coerce")
    v.dropna(subset=["date"], inplace=True)

    # new_visit=v.iloc[:, [1, 0, 2, 13, 14, 15, 16, 26, 27, 29, 21, 11, 6, 7, 12, 33, 43, 47, 50]]
    # new_visit.columns=["id", "patient_id", "date", "ncnormalresidualtissue", "ncsuspiciousresidualtissue",
    #                    "ncsuspiciouslympnodes",
    #                    "ncifsuspiciouslympnodespresent", "imgsuspiciousneck", "imgsuspiciousdistantmeta",
    #                    "dsevidence", "raiuptake", "lbtgab", "lb_basaltg", "lblstimulatedtg", "lbtgablevels", "trrai",
    #                    "trsurgery", "trexternalradio", "trother"]

    new_visit = v[[
        "id", "patient_id", "date",
        "ncnormalresidualtissue",
        "ncsuspiciousresidualtissue",
        "ncsuspiciouslympnodes",
        "ncifsuspiciouslympnode",
        "imgsuspiciousneck",
        "imgsuspiciousdistantmeta",
        "lbtgassaysfnsensitivity",
        "dsevidence",
        "raiuptake",
        "lbtgab",
        "lb_basaltg",
        "lblstimulatedtg",
        "lbtgablevels",
        "trrai",
        "trsurgery",
        "trexternalradio",
        "trother",
        "laboratory_complete",
        "neck_us_complete",
        "other_imaging_studies_complete",
        "disease_status_complete",
        "rai_scan_complete"
    ]].copy()

    new_visit["id"] = range(1, len(new_visit) + 1)

    #new_visit = new_visit.drop(new_visit[new_visit['patient_id'] == 'Patient_id'].index)
    #new_visit=new_visit[pd.to_numeric(new_visit['id'], errors='coerce').notnull()]

    new_visit = new_visit[
        (new_visit["patient_id"] != "Patient_id") &
        pd.to_numeric(new_visit["id"], errors="coerce").notnull()
    ]
    # rilassiamo temporaneamente il vincolo
    # per il patient_id di essere numerico, a causa della
    # presenza dei - nei record id
    #new_visit.patient_id = pd.to_numeric(new_visit.patient_id)

    if filter_on_patient:
        new_visit = new_visit[new_visit['patient_id'].isin(patients_selection)]

    # nel formato v2 le date sono nella forma US
    #new_visit.date =new_visit.date.apply(lambda x: dateparser.parse(x, languages=['it']))
    #new_visit.date = new_visit.date.apply(lambda x: dateparser.parse(x))

    new_visit['trrai'] = new_visit['trrai'].replace({1: 0, 2: 1})
    new_visit['trsurgery'] = new_visit['trsurgery'].replace({1: 0, 2: 1})
    new_visit['trexternalradio'] = new_visit['trexternalradio'].replace({1: 0, 2: 1})
    new_visit['trother'] = new_visit['trother'].replace({1: 0, 2: 1})

    # NaN are automatically converted to NaT, by means of errors=coerce
#    new_visit['date']=pd.to_datetime(new_visit['date'],errors='coerce')
#    new_visit=new_visit.fillna(
#        {'ncifsuspiciouslympnode': 0, 'imgsuspiciousneck': 0, 'imgsuspiciousdistantmeta': 0, 'dsevidence': 0,
#         'raiuptake': 0, 'lbtgab': 0, 'lb_basaltg': 0, 'lbtgablevels': 0})

    # Disattiviamo il filling automatico degli na dal momento
    # che questi casi (na) sono gestiti dal codice successivo
    new_visit = new_visit.fillna({'lbtgablevels': 0})


    new_visit.id = pd.to_numeric(new_visit.id, downcast='integer')
    new_visit.ncnormalresidualtissue = pd.to_numeric(new_visit.ncnormalresidualtissue, downcast='integer')
    new_visit.ncsuspiciousresidualtissue = pd.to_numeric(new_visit.ncsuspiciousresidualtissue, downcast='integer')
    new_visit.ncsuspiciouslympnodes = pd.to_numeric(new_visit.ncsuspiciouslympnodes, downcast='integer')
    new_visit.ncifsuspiciouslympnode = pd.to_numeric(new_visit.ncifsuspiciouslympnode, downcast='integer')
    new_visit.imgsuspiciousneck = pd.to_numeric(new_visit.imgsuspiciousneck, downcast='integer')
    new_visit.imgsuspiciousdistantmeta = pd.to_numeric(new_visit.imgsuspiciousdistantmeta, downcast='integer')
    new_visit.dsevidence = pd.to_numeric(new_visit.dsevidence, downcast='integer')
    new_visit.raiuptake = pd.to_numeric(new_visit.raiuptake, downcast='integer')
    new_visit.lbtgab = pd.to_numeric(new_visit.lbtgab, downcast='integer')
    new_visit.lb_basaltg = pd.to_numeric(new_visit.lb_basaltg)
    new_visit.lblstimulatedtg = pd.to_numeric(new_visit.lblstimulatedtg)
    new_visit.lbtgablevels = pd.to_numeric(new_visit.lbtgablevels)
    new_visit.trrai = pd.to_numeric(new_visit.trrai, downcast='integer')
    new_visit.trsurgery = pd.to_numeric(new_visit.trsurgery, downcast='integer')
    new_visit.trexternalradio = pd.to_numeric(new_visit.trexternalradio, downcast='integer')
    new_visit.laboratory_complete = pd.to_numeric(new_visit.laboratory_complete, downcast='integer')
    new_visit.neck_us_complete = pd.to_numeric(new_visit.neck_us_complete, downcast='integer')
    new_visit.other_imaging_studies_complete = pd.to_numeric(new_visit.other_imaging_studies_complete, downcast='integer')
    new_visit.disease_status_complete = pd.to_numeric(new_visit.disease_status_complete, downcast='integer')
    new_visit.rai_scan_complete = pd.to_numeric(new_visit.rai_scan_complete, downcast='integer')

    print(f"Overall number of visits: {len(new_visit.index)} ")
    return new_visit


print(f'Loading patients from file {patients_path}')
patient = load_patients_v2(patients_path)
print(f'Loading surgeries from file {surgeries_path}')
surgery = load_surgery_v2(surgeries_path)
print(f'Loading visits from file {visits_path}')
visit = load_visits_v2(visits_path)

if filter_on_patient:
    patient=patient[patient['id'].isin(patients_selection)]

# Applicazione criteri di esclusione su patient

initial_exclusion = dict()
excluded_visit = dict()

first_exclusion_vis_1 = dict()
first_exclusion_vis_2 = dict()
first_exclusion_vis_3 = dict()

missing_surgery = dict()
missing_visit = dict()

no6mvisits = 0

if perform_exclusion:

    # Inizializza i contatori per ciascun criterio
    patient_exclusion_criteria1 = 0  # Carcinoma midollare
    patient_exclusion_criteria2 = 0  # Carcinoma anaplastico
    patient_exclusion_criteria3 = 0  # UMP
    patient_exclusion_criteria4 = 0  # NIFTP
    patient_exclusion_criteria5 = 0  # Trattamento incompleto
    patient_exclusion_criteria6 = 0  # Trattamento completo ma RRA mancante o nullo

    # 1. Carcinoma midollare della tiroide (“Histology cancer type”=2)
    for pid in patient.loc[patient['hicancertype'] == 2, 'id']:
        initial_exclusion[pid] = 1
        patient_exclusion_criteria1 += 1

    # 2–4. Histology subtypes = 12 (anaplastico), 11 (UMP), 14 (NIFTP)
    for pid, subtype in patient.loc[
        patient['hihistologicsubtypes'].isin([11, 12, 14]), ['id', 'hihistologicsubtypes']].values:
        initial_exclusion[pid] = 1
        if subtype == 12:
            patient_exclusion_criteria2 += 1
        elif subtype == 11:
            patient_exclusion_criteria3 += 1
        elif subtype == 14:
            patient_exclusion_criteria4 += 1

    # 5. Trattamento iniziale incompleto (initial_treatment_complete = 0)
    for pid in patient.loc[patient['initial_treatment_complete'] == 0, 'id']:
        initial_exclusion[pid] = 1
        patient_exclusion_criteria5 += 1

    # 6. Trattamento completo ma RRA mancante o nullo
    for pid in patient.loc[
        (patient['initial_treatment_complete'] == 1) &
        (patient['rra'].isna() | (patient['rra'] == 0)),
        'id'
    ]:
        initial_exclusion[pid] = 1
        patient_exclusion_criteria6 += 1

    # Stampa finale dei conteggi
    print(f"Patient exclusion criteria 1: {patient_exclusion_criteria1}")
    print(f"Patient exclusion criteria 2: {patient_exclusion_criteria2}")
    print(f"Patient exclusion criteria 3: {patient_exclusion_criteria3}")
    print(f"Patient exclusion criteria 4: {patient_exclusion_criteria4}")
    print(f"Patient exclusion criteria 5: {patient_exclusion_criteria5}")
    print(f"Patient exclusion criteria 6: {patient_exclusion_criteria6}")

    log_debug(f'Total initial exclusions: {len(initial_exclusion)} patients')

    # Filtra il dataframe escludendo i pazienti individuati
    patient = patient[~patient['id'].isin(initial_exclusion.keys())]

    # Applicazione criteri di esclusione su visit

    exclusion_criteria1 = 0
    exclusion_criteria2 = 0
    exclusion_criteria3 = 0
    exclusion_criteria4 = 0
    exclusion_criteria5 = 0
    exclusion_criteria6 = 0

    for index, row in visit.iterrows():
        v_id = row['id']

        # 1. CRF incomplete o non verificate
        if row['laboratory_complete'] in [0, 1] or \
                row['neck_us_complete'] in [0, 1] or \
                row['disease_status_complete'] in [0, 1]:
            excluded_visit[row['id']] = 1
            first_exclusion_vis_1[row['patient_id']] = 1
            exclusion_criteria1 += 1
            continue


        # 2. Mancante Tireoglobulina [Laboratory Basal Tg (ng/mL) missing AND Laboratory Stimulated Tg (ng/mL) missing]
        if pd.isna(row['lb_basaltg']) and pd.isna(row['lblstimulatedtg']):
            excluded_visit[row['id']] = 1
            first_exclusion_vis_1[row['patient_id']] = 1
            exclusion_criteria3 += 1
            continue

        # 3. Mancante anticorpi anti-tireoglobulina [Laboratory TgAb avalable=0]
        if pd.isna(row['lbtgab']):
            excluded_visit[row['id']] = 1
            first_exclusion_vis_1[row['patient_id']] = 1
            exclusion_criteria4 += 1
            continue

        # 4. Mancante ecografia [Neck US normal residual tissue=0 OR Neck US suspicious tissue in thyroid bed=0 OR Neck US suspicious lymph nodes=0]
        if pd.isna(row['ncnormalresidualtissue']) or pd.isna(row['ncsuspiciousresidualtissue']) or pd.isna(
                row['ncsuspiciouslympnodes']):
            excluded_visit[row['id']] = 1
            first_exclusion_vis_1[row['patient_id']] = 1
            exclusion_criteria5 += 1
            continue

        # 5. Visita precedente al 2013 (visit_date < 01/01/2013)
        if row['date'] < pd.Timestamp("2013-01-01"):
            excluded_visit[row['id']] = 1
            first_exclusion_vis_1[row['patient_id']] = 1
            exclusion_criteria6 += 1
            continue

if perform_exclusion:
    print(f'Exclusion criteria 1:  {exclusion_criteria1}')
    print(f'Exclusion criteria 2:  {exclusion_criteria2}')
    print(f'Exclusion criteria 3:  {exclusion_criteria3}')
    print(f'Exclusion criteria 4:  {exclusion_criteria4}')
    print(f'Exclusion criteria 5:  {exclusion_criteria5}')
    print(f'Exclusion criteria 6:  {exclusion_criteria6}')


# def get_values_from_prev_visit_old(row):
#     patient_id = row["patient_id"]
#     current_date = row["date"]
#
#     # Cerca visite precedenti dello stesso paziente
#     previous_visits = visit[
#         (visit["patient_id"] == patient_id) &
#         (visit["date"] < current_date)
#     ]
#
#     if previous_visits.empty:
#         return pd.Series(
#             [-1, -1, -1, -1, -1, -1],
#             index=[
#                 "prev_id", "prev_lbtgab", "prev_lbtgablevels", "prev_lb_basaltg",
#                 "var_lbtgablevels", "var_lb_basaltg"
#             ]
#         )
#
#     # Estrai la visita precedente più recente
#     prev_row = previous_visits.loc[previous_visits["date"].idxmax()]
#
#     prev_id = int(prev_row.get("id", -1))
#     prev_lbtgab = int(prev_row.get("lbtgab", -1))
#     prev_lbtgablevels = float(prev_row.get("lbtgablevels", -1))
#     prev_lb_basaltg = float(prev_row.get("lb_basaltg", -1))
#
#     # Calcolo delle variazioni (percentuali), con fallback a -1
#     if pd.notna(row["lbtgablevels"]) and pd.notna(prev_lbtgablevels) and prev_lbtgablevels != 0:
#         var_lbtgablevels = ((row["lbtgablevels"] - prev_lbtgablevels) / prev_lbtgablevels) * 100
#     else:
#         var_lbtgablevels = -1
#
#     if pd.notna(row["lb_basaltg"]) and pd.notna(prev_lb_basaltg) and prev_lb_basaltg != 0:
#         var_lb_basaltg = ((row["lb_basaltg"] - prev_lb_basaltg) / prev_lb_basaltg) * 100
#     else:
#         var_lb_basaltg = -1
#
#     return pd.Series([
#         prev_id,
#         prev_lbtgab,
#         prev_lbtgablevels,
#         prev_lb_basaltg,
#         var_lbtgablevels,
#         var_lb_basaltg
#     ], index=[
#         "prev_id", "prev_lbtgab", "prev_lbtgablevels", "prev_lb_basaltg",
#         "var_lbtgablevels", "var_lb_basaltg"
#     ])

# Individuo la visita precedente più recent e calcolo
# le variazioni percentuali per i due parametri
def get_values_from_prev_visit(row):
    patient_id = row["patient_id"]
    current_date = row["date"]

    # Cerchiamo le visite dello stesso paziente con data precedente
    previous_visits = visit[
        (visit["patient_id"] == patient_id) &
        (visit["date"] < current_date)
    ]

    if previous_visits.empty:
        return pd.Series(
            [-1, -1, -1, -1, -1, -1, -1, -1],
            index=[
                "prev_id", "prev_lbtgab", "prev_lbtgablevels", "prev_lb_basaltg",
                "var_lbtgablevels", "var_lb_basaltg", "abs_lbtgablevels", "abs_lb_basaltg"
            ]
        )


    # Estrae la visita più vicina nel tempo
    prev_row = previous_visits.loc[previous_visits["date"].idxmax()]

    # Estrai i valori precedenti
    prev_id = int(prev_row["id"])
    prev_lbtgab = int(prev_row["lbtgab"]) if pd.notna(prev_row["lbtgab"]) else 0
    prev_lbtgablevels = int(prev_row["lbtgablevels"])
    prev_lb_basaltg = float(prev_row["lb_basaltg"])

    # Calcolo in linea della variazione percentuale
    if pd.notna(row["lbtgablevels"]) and pd.notna(prev_lbtgablevels) and prev_lbtgablevels != 0:
        var_lbtgablevels = ((row["lbtgablevels"] - prev_lbtgablevels) / prev_lbtgablevels) * 100
    else:
        var_lbtgablevels = None

    if pd.notna(row["lb_basaltg"]) and pd.notna(prev_lb_basaltg) and prev_lb_basaltg != 0:
        var_lb_basaltg = ((row["lb_basaltg"] - prev_lb_basaltg) / prev_lb_basaltg) * 100
    else:
        var_lb_basaltg = None

    # Calcolo differenze assolute
    if pd.notna(row["lbtgablevels"]) and pd.notna(prev_lbtgablevels):
        abs_lbtgablevels = (row["lbtgablevels"] - prev_lbtgablevels)
    else:
        abs_lbtgablevels = None

    if (
            pd.notna(row["lb_basaltg"]) and
            pd.notna(prev_lb_basaltg) and
            pd.notna(row["lbtgassaysfnsensitivity"]) and
            row["lb_basaltg"] >= row["lbtgassaysfnsensitivity"]
    ):
        abs_lb_basaltg = row["lb_basaltg"] - prev_lb_basaltg
    else:
        abs_lb_basaltg = None

    return pd.Series([
        prev_id,
        prev_lbtgab,
        prev_lbtgablevels,
        prev_lb_basaltg,
        var_lbtgablevels,
        var_lb_basaltg,
        abs_lbtgablevels,
        abs_lb_basaltg
    ], index=[
        "prev_id",
        "prev_lbtgab",
        "prev_lbtgablevels",
        "prev_lb_basaltg",
        "var_lbtgablevels",
        "var_lb_basaltg",
        "abs_lbtgablevels",
        "abs_lb_basaltg"
    ])
if not visit.empty:
    xxx = visit.apply(get_values_from_prev_visit, axis=1)
    visit[[
        "prev_id", "prev_lbtgab", "prev_lbtgablevels", "prev_lb_basaltg",
        "var_lbtgablevels", "var_lb_basaltg", "abs_lbtgablevels", "abs_lb_basaltg"
    ]] = xxx


p_ata_risk = dict()

if eval_ata_risk:

    ### Pazienti a rischio alto= (una qualsiasi delle seguenti condizioni)
    patient_h_risk = patient.copy()

    #  FTC invasivo (FTC con invasione vascolare) ["Histology subtypes" = 8]
    cond1_h = patient_h_risk['hihistologicsubtypes'] == 8

    #  ["Histology subtypes"= 6, 7, 9 AND "Histology vascular invasion" = 2]
    cond2_h = (patient_h_risk['hihistologicsubtypes'].isin([6, 9])) & (patient_h_risk['hivascolarinvasion'] == 2)

    #  Estensione extratiroidea macroscopica ["Histology extra-thyroid extension" &gt;2]
    cond3_h = (
            (patient_h_risk['hiextraextension'] > 2)
    )

    #  Metastasi linfonodali >=3 cm ["Histology lymph node size" &gt;30 mm]
    cond4_h = (
            (patient_h_risk['hylympnodesize'] >= 30)
    )

    #  Resezione R2 ["Histology surgical margins" = 3]
    cond5_h = patient_h_risk['hysurgicalmargins'] == 3

    # Metastasi alla diagnosi ["M value"=3 OR "M value calculate"=3]
   # cond6_h = (patient_h_risk['satoptm']==3) | (patient_h_risk['forcedm']==3)
    cond6_h = (patient_h_risk['satoptm'] == 1)

    patient_h_risk= patient_h_risk[cond1_h|cond2_h|cond3_h|cond4_h|cond5_h|cond6_h]

    ### Pazienti a rischio intermedio
    patient_lm_risk = patient.copy()

    # PTC (eccetto variante Tall Cell, scarsamente differenziato, sclerosante) FTC minimamente invasivo
    # ["Histology subtypes", tutti i valori eccetto 4, 8, 13] AND
    cond1 = patient_lm_risk['hihistologicsubtypes'].isin([1, 2, 3, 5, 6, 7, 9, 11, 12, 14, 15])

    # Assenza di invasione vascolare ["Histology vascular invasion" diverso da 2] AND
    cond2 = patient_lm_risk['hivascolarinvasion'].isin([1,3])

    # 1- Estensione extratiroidea microscopica ["Histology extra-thyroid extension" =2] OR
    cond3 = patient_lm_risk['hiextraextension'] == 2

    # 2- Presenza di massimo 5 metastasi del compartimento centrale ["Histology lymph node metastases" = 3
    # AND "Histology number of metastatic L. nodes" = numero compreso tra 1 e 5]
    cond4 = patient_lm_risk['hilymphnodemetastasis'] == 3

    cond5 = (
            (patient_lm_risk['hilymphnodemetastasisnum'] >= 1) &
            (patient_lm_risk['hilymphnodemetastasisnum'] <= 5)
    )

    cond6 = patient_lm_risk['hihistologicsubtypes'].isin([4,13])
    cond7 = patient_lm_risk['hilymphnodemetastasis'] == 3
    cond8 = patient_lm_risk['hilymphnodemetastasisnum'] > 5
    cond9 = patient_lm_risk['hilymphnodemetastasis'] > 3
    cond10 = patient_lm_risk['hihistologicsubtypes'].isin([1,2,3,4,5,10])
    cond11 = patient_lm_risk['hivascolarinvasion'] == 2

    patient_lm_risk = patient_lm_risk[
        (cond1 & cond2 & (cond3 | (cond4 & cond5))) |
        cond6 |
        (cond7 & cond8) |
        cond9 |
        (cond10 & cond11)
        ]


    ### Pazienti a rischio basso=
    # PTC (eccetto variante Tall Cell, scarsamente differenziato, sclerosante) FTC minimamente invasivo

    patient_l_risk = patient.copy()
    # ["Histology subtypes" tutti i valori eccetto 4, 8, 13] AND
    #    cond1 = ~patient_l_risk['hihistologicsubtypes'].str.endswith(('.4','.8','.13'))
    cond1 = patient_l_risk['hihistologicsubtypes'].isin([1, 2, 3, 5, 6, 7, 9, 11, 12, 14, 15])


    # Assenza di invasione vascolare ["Histology vascular invasion" diverso da 2] AND
    # patient_l_risk = patient_l_risk[~patient_l_risk['hivascolarinvasion'].str.endswith('.2')]
    cond2 = patient_l_risk['hivascolarinvasion'].isin([1,3])

    # Assenza o status metastasi linfonodali sconosciuto ["Histology lymph node metastases" = 1, 2] AND
    # patient_l_risk = patient_l_risk[patient_l_risk['hilymphnodemetastasis'].str.endswith(('1','2'))]
    # 22/7/2020: Assenza o status metastasi linfonodali sconosciuto [“Histology lymph node metastases” = 0, 1, 2]
    cond3=patient_l_risk['hilymphnodemetastasis'].isna() | patient_l_risk['hilymphnodemetastasis'].isin([1, 2])

    # Resezione R0-R1 ["Histology surgical margins" diverso da 3] AND
    # patient_l_risk = patient_l_risk[~patient_l_risk['hysurgicalmargins'].str.endswith('.3')]
    #   cond4 = ~patient_l_risk['hysurgicalmargins'].str.endswith('.3')
    cond4 = patient_l_risk['hysurgicalmargins'].isna() | patient_l_risk['hysurgicalmargins'].isin([1, 2])

    # Estensione extratiroidea assente ["Histology extra-thyroid extension" =1]
    # patient_l_risk = patient_l_risk[patient_l_risk['hiextraextension'].astype(int) == 1]
    cond5 = patient_l_risk['hiextraextension'] == 1
    patient_l_risk = patient_l_risk[(cond1 & cond2 & cond3 & cond4 & cond5)]


    # Set iniziali
    all_ids = set(patient['id'].unique())

    # Assegnazioni gerarchiche: LOW → INTERMEDIATE → HIGH
    ph = set(patient_h_risk['id'].unique())
    plm = set(patient_lm_risk['id'].unique()) - ph
    pl = set(patient_l_risk['id'].unique()) - ph - plm

    # Costruzione dizionario rischio
    p_ata_risk = {}

    for p_id in pl:
        p_ata_risk[p_id] = "LOW RISK"

    for p_id in plm:
        p_ata_risk[p_id] = "INTERMEDIATE RISK"

    for p_id in ph:
        p_ata_risk[p_id] = "HIGH RISK"

    # Pazienti non classificati
    unclassified = all_ids - set(p_ata_risk.keys())

    for p_id in unclassified:
        p_ata_risk[p_id] = "UNKNOWN"

    log_debug("\nATA risk evaluation results")
    log_debug(f"Number of unclassified patients: {len(unclassified)}")
    log_debug("Number of high risk patients: " + str(len(patient_h_risk.index)))
    log_debug("Number of intermediate risk patients: " + str(len(patient_lm_risk.index)))
    log_debug("Number of low risk patients: " + str(len(patient_l_risk.index)))


output_list = []

count = 0
missing_visits_count = 0
missing_surgery_count = 0

# Dato un paziente, quante delle visite ricadono nell'intervallo [6,18]
visits_count_12m = 0

# Dato un paziente, quante delle visite ricadono nell'intervallo [6,18] e non sono filtrate dai criteri di esclusione
included_visits_count_12m = 0

print(f'Processing {len(patient)} patients:')

visits_by_patient = dict(tuple(visit.groupby("patient_id")))
surgery_by_patient = dict(tuple(surgery.groupby("patient_id")))

# For each patient
for p, row in patient.iterrows():
    if use_v2:
        p = row['id']
    else:
        p = int(row['id'])
        birth_date = row['birthdate']

    rradate = row['rradate']
    rra = row['rra']

    if rra == 2 and pd.isna(rradate):
        missing_rra_date = 1
    else:
        missing_rra_date = 0


    count += 1
    if count%1000 == 0:
        print(count)


    visits_count_12m = 0
    included_visits_count_12m = 0

    treatment = 0
    rtt_5y = -2
    rtt_3y = -2
    rtt_12m = -2
    rtt_latest = -2

    # We extract all his visits and surgeries
#    visits = visit[visit['patient_id'] == p]
#    surgeries = surgery[surgery['patient_id'] == p]
    visits = visits_by_patient.get(p, pd.DataFrame())
    surgeries = surgery_by_patient.get(p, pd.DataFrame())

    last_sgcentralcompartmentneckdissection = -1
    last_sglateralcompartmentneckdissection = -1
    last_prophylacticcentralneckdissection  = -1

    if not surgeries.empty:
        if (surgeries['sgcentralcompartmentneckdissection'] == 2).any():
            last_sgcentralcompartmentneckdissection = 2

        #        last_sglateralcompartmentneckdissection = s['sglateralcompartmentneckdissection'].squeeze()

        if (surgeries['sglateralcompartmentneckdissection'] == 2).any():
            last_sglateralcompartmentneckdissection = 2

        #        last_prophylacticcentralneckdissection = s['prophylacticcentralneckdissection'].squeeze()

        if (surgeries['prophylacticcentralneckdissection'] == 2).any():
            last_prophylacticcentralneckdissection = 2

        surgeries = surgeries[surgeries['sgapproach'].notna()]

    surgery_count = len(surgeries.index)
    # We pre evaluate a condition required for TT alone case during rtt evaluation
    if surgery_count == 2 and len(surgery[surgery['sgapproach']==3].index) == 2:
        row['two_sgapproach_three'] = True
    else:
        row['two_sgapproach_three'] = False
    row['surgery_count'] = surgery_count


    last_surgery_approach = -1




    most_recent_date = row['dt_initial_treatment']

    if surgery_count>0:
        oldest_date = min(surgeries['sgdateofsurgery'])



        # We override the previous method used for establishing the
        # most recent date by looking straightly at the dt_initial_treatment variable


        if pd.isna(row['dt_initial_treatment']):
            if perform_exclusion:
                continue

        if rra == 2:
            most_recent_date_old_alg = rradate
            # Se Table Patients, RRA=2; [differenza RRA date [Table Patients] - Visit Date[Table Visits]
            # Se RRA date is null, [differenza date of Surgery[prima occorrenza, Table Surgery] - Visit Date[Table Visits]
            if pd.isnull(most_recent_date_old_alg):
                most_recent_date_old_alg = max(surgeries['sgdateofsurgery'])
        elif rra == 1:
            # Se Table Patients, RRA=1; [differenza date of Surgery[prima occorrenza, Table Surgery] - Visit Date[Table Visits]
            most_recent_date_old_alg = max(surgeries['sgdateofsurgery'])

        # Independently of the value of rra, we also consider as surgery the most recent one
        #        s = surgeries[surgeries['sgdateofsurgery'] == most_recent_date]
        s = surgeries[surgeries['sgdateofsurgery'] == max(surgeries['sgdateofsurgery'])]
        last_surgery_approach = s['sgapproach'].squeeze()

        #last_sgcentralcompartmentneckdissection = s['sgcentralcompartmentneckdissection'].squeeze()


        if use_v2:
            patient_age = row['age']
        else:
            patient_age = get_age(birth_date, oldest_date)
    else:
        if debug:
            print('patient: ' + str(p) + " does not exists in surgery table")
        missing_surgery_count += 1
        missing_surgery[p] = 1
        if skip_missing_surgery:
            continue


    if visits.empty:
        if debug:
            print('patient: ' + str(p) + " does not exists in visits table")
        missing_visits_count += 1
        missing_visit[p] = 1
        if skip_missing_visit:
            continue


    # E' presente almeno un caso di paziente con età negativa (id=11765),
    # la data di intervento è di mesi inferiore alla data di nascita
    if debug:
        print('patient: ' + str(p) + " age: " + str(patient_age))

    record = {}

    visit_exclusion_5y = False
    visit_exclusion_3y = False
    visit_exclusion_12m = False

    if p not in missing_visit:

        # Calcolo rtt_all
        rtt_all = get_all_rtt_for_patient(visits, s, row, mode)

        reference_date = most_recent_date

        # Response 5 years after
        five_years_after = most_recent_date + datetime.timedelta(5 * 365)
        rtt_old_5y, rtt_new_5y, treatment, reference_date_5y = get_new_rtt(five_years_after, visits, s, row, mode)

        # Response 3 years after
        three_years_after = most_recent_date + datetime.timedelta(3 * 365)
        rtt_old_3y, rtt_new_3y, treat, reference_date_3y = get_new_rtt(three_years_after, visits, s, row, mode)
        if treatment == 0:
            treatment = treat

        # Response 12 months after
        twelve_months_after = most_recent_date + datetime.timedelta(365)
        rtt_old_12m, rtt_new_12m, treat, reference_date_12m = get_new_rtt(twelve_months_after, visits, s, row, mode)
        if treatment == 0:
            treatment = treat

        if rtt_12m == -2:
            no6mvisits += 1
        # First 12 months treatments

        record['rtt_all'] = rtt_all

        record['treat_012m'] = visits[(visits['date'] > most_recent_date) & (visits['date'] < twelve_months_after)][['trrai','trsurgery','trother','trexternalradio']].any(axis=1).sum()
        record['treat_1236m'] = visits[(visits['date'] > twelve_months_after) & (visits['date'] < three_years_after)][['trrai','trsurgery','trother','trexternalradio']].any(axis=1).sum()
        record['treat_3660m']=visits[(visits['date'] > three_years_after) & (visits['date'] < five_years_after)][['trrai','trsurgery','trother','trexternalradio']].any(axis=1).sum()

        record['reference_date'] = reference_date
        record['reference_date_12m'] = reference_date_12m
        record['reference_date_3y'] = reference_date_3y
        record['reference_date_5y'] = reference_date_5y

        # If one of the reference dates does not exists, we fall back to standard (12m, 3y, 5y) dates
        if reference_date_12m is None:
            reference_date_12m = twelve_months_after

        if reference_date_3y is None:
            reference_date_3y = three_years_after

        if reference_date_5y is None:
            reference_date_5y = five_years_after

        record['treat2_012m'] = visits[(visits['date'] > most_recent_date) & (visits['date'] < reference_date_12m)][['trrai','trsurgery','trother','trexternalradio']].any(axis=1).sum()
        record['treat2_1236m'] = visits[(visits['date'] > reference_date_12m) & (visits['date'] < reference_date_3y)][['trrai','trsurgery','trother','trexternalradio']].any(axis=1).sum()
        record['treat2_3660m']=visits[(visits['date'] > reference_date_3y) & (visits['date'] < reference_date_5y)][['trrai','trsurgery','trother','trexternalradio']].any(axis=1).sum()

        # Aggiunto per fini di debug.
        # Per ogni visita di un certo paziente a +/- 6m di distanza dalla data di riferimento:
        # - incrementiamo visits_count_12m di 1
        # - incrementiamo included_visits_count_12m di 1 se non e' stato precedentemente escluso
        for i, cur_v in visits.iterrows():
            if get_month_diff(cur_v['date'], twelve_months_after)<6:
                visits_count_12m += 1
                if cur_v['id'] not in excluded_visit:
                    included_visits_count_12m += 1


        # Response latest visit
        rtt_old_latest, rtt_new_latest, treat = get_new_rtt_latest(visits, s, row, mode)
        if treatment == 0:
            treatment = treat


    else:
        if perform_exclusion:
            first_exclusion_vis_3[p] = 1
            continue

    if treatment == 3 and surgeries["sgapproach"].dropna().shape[0] > 1:
        lobectomy_check = 1
    else:
        lobectomy_check = 0

    record['patient_id'] = p
    record['rtt_old_5y'] = rtt_old_5y
    record['rtt_old_3y'] = rtt_old_3y
    record['rtt_old_12m'] = rtt_old_12m
    record['rtt_old_latest'] = rtt_old_latest

    record['rtt_new_5y'] = rtt_new_5y
    record['rtt_new_3y'] = rtt_new_3y
    record['rtt_new_12m'] = rtt_new_12m
    record['rtt_new_latest'] = rtt_new_latest

    record['ata_risk'] = p_ata_risk[p]
    record['age'] = patient_age
    record['sex'] = row['sex']
    record['rra'] = row['rra']
    record['tcddiagnosis'] = row['tcddiagnosis']
    record['sgapproach'] = last_surgery_approach

    record['sgcentralcompartmentneckdissection'] = last_sgcentralcompartmentneckdissection
    record['sglateralcompartmentneckdissection'] = last_sglateralcompartmentneckdissection
    record['prophylacticcentralneckdissection'] = last_prophylacticcentralneckdissection

    record['hihistologicsubtypes'] = row['hihistologicsubtypes']
    record['hitumorsize'] = row['hitumorsize']
    record['hitumoralfoci'] = row['hitumoralfoci']
    record['hiextraextension'] = row['hiextraextension']
    record['invasionofstrapmuscles'] = row['invasionofstrapmuscles']
    record['hilymphnodemetastasis'] = row['hilymphnodemetastasis']
    record['hinumberofremovedlymphnodes'] = row['hinumberofremovedlymphnodes']
    record['clinicalcentre_id'] = row['clinicalcentre_id']
    record['satoptm'] = row['satoptm']
    record['forcedm'] = row['forcedm']
    record['external_ata_risk'] = row['external_ata_risk']
    record['hysurgicalmargins'] = row['hysurgicalmargins']
    record['rraradioiodineactivity'] = row['rraradioiodineactivity']
    record['rraradioiodineactivitynum'] = row['rraradioiodineactivitynum']
    record['hivascolarinvasion'] = row['hivascolarinvasion']
    record['treatment'] = treatment
    record['first_exclusion'] = initial_exclusion.get(p, 0)
    record['first_exclusion_vis_1'] = first_exclusion_vis_1.get(p, 0)
    record['first_exclusion_vis_2'] = first_exclusion_vis_2.get(p, 0)
    record['first_exclusion_vis_3'] = first_exclusion_vis_3.get(p, 0)
    record['missing_visit'] = missing_visit.get(p, 0)
    record['missing_surgery'] = missing_surgery.get(p, 0)
    record['visits_count_12m'] = visits_count_12m
    record['included_visits_count_12m'] = included_visits_count_12m
    record['dt_initial_treatment'] = row['dt_initial_treatment']
    record['reference_date_old_alg'] = most_recent_date_old_alg
    record['lobectomy_check'] = lobectomy_check
    record['missing_rra_date'] = missing_rra_date

    output_list.append(record)

print(f"Total patients processed: {count}")
if skip_missing_visit:
    print(f"Excluded {missing_visits_count} patients without visits")
if skip_missing_surgery:
    print(f"Excluded {missing_surgery_count} patients without surgeries")

print(f"Patients with valid output: {len(output_list)}")
print(f"Patients skipped during main loop: {count - len(output_list)}")

print(f'Saving final report to files: {xls_output_file}, {csv_output_file}')


output = pd.DataFrame(output_list, columns=[
    'patient_id',
    'treatment', 'rtt_old_5y', 'rtt_old_3y', 'rtt_old_12m', 'rtt_old_latest',
    'rtt_new_5y', 'rtt_new_3y', 'rtt_new_12m', 'rtt_new_latest', 'rtt_all',
    'ata_risk', 'external_ata_risk',
    'first_exclusion', 'first_exclusion_vis_1', 'first_exclusion_vis_2', 'first_exclusion_vis_3',
    'missing_visit', 'missing_surgery', 'visits_count_12m', 'included_visits_count_12m',
    'lobectomy_check', 'missing_rra_date',
    'treat2_012m', 'treat2_1236m', 'treat2_3660m',
    'dt_initial_treatment',
    'reference_date_old_alg', 'reference_date', 'reference_date_12m', 'reference_date_3y', 'reference_date_5y','prophylacticcentralneckdissection','sgcentralcompartmentneckdissection','sglateralcompartmentneckdissection'
])


# Identifica le righe con valori discordanti di ata risk
ata_risk_discordanti = output[output['ata_risk'] != output['external_ata_risk']]

# Verifica se ci sono discrepanze
if not ata_risk_discordanti.empty:
    print("Discrepanze trovate tra 'ata_risk' ed 'external_ata_risk':")
    # Mostra l'elenco dei pazienti con i valori discordanti
    for _, row in ata_risk_discordanti.iterrows():
        print(f"Patient ID: {row['patient_id']}, ata_risk: {row['ata_risk']}, external_ata_risk: {row['external_ata_risk']}")
else:
    print("Nessuna discrepanza trovata tra 'ata_risk' ed 'external_ata_risk'.")

output.to_excel(xls_output_file, index=False)
output.to_csv(csv_output_file,index=False)