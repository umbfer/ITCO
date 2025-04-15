import pandas as pd
import datetime
import dateparser
import warnings

#
# Script per il trattamento e l'analisi dei dati ITCO
# Umberto Ferraro Petrillo
# Ultima revisione: 24/12/24


# Input and output files

patients_path = "../../Downloads/ITCO/dati/giu_2022/patients_giu2022.csv"
surgeries_path = "../../Downloads/ITCO/dati/giu_2022/surgeries_giu2022.csv"
visits_path = "../../Downloads/ITCO/dati/giu_2022/visits_giu2022.csv"

patients_path = "data/patient_23.01.csv"
surgeries_path = "data/surgery_23.01.csv"
visits_path = "data/visits_23.01.csv"

xls_output_file= 'output/output_short.xls'
csv_output_file= 'output/output_short.csv'

# Variabili configurazione

# Se diverso da None, processa unicamente il paziente di cui si fornisce l'id
# Esempio: utilizzando la seguente definizione la procedura sarà fatta girare
# per il solo paziente con id 1234
# filter_on_patient = 1234

filter_on_patient = "1-36071"
filter_on_patient = None


use_v2 = True

# Se True, valuta i criteri di inclusione/esclusione
perform_exclusion = True
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


def get_last_surgery(p):
    surgeries = surgery[surgery['patient_id'] == p]
    if len(surgeries.index)==0:
        return None

    date = max(surgeries['sgdateofsurgery'])
    return surgeries[surgeries['sgdateofsurgery'] == date].sample(n=1).squeeze()


def get_first_surgery(p):
    surgeries=surgery[surgery['patient_id'] == p]

    if len(surgeries.index) == 0:
        return None

    date=min(surgeries['sgdateofsurgery'])
    return surgeries[surgeries['sgdateofsurgery'] == date].sample(n=1).squeeze()



def get_month_diff(a, b):
    return abs(12 * (a.year - b.year) + (a.month - b.month))


def get_response_to_treatment1(p, v, s):

    if v['ncifsuspiciouslympnodespresent'] == 2 or v['imgsuspiciousneck'] == 2 or v[
            'imgsuspiciousdistantmeta'] == 2 or v['raiuptake'] > 2:
        if debug:
                print('Structural incomplete')
        return 2
    elif v['ncsuspiciouslympnodes'] in [0,1] and v['imgsuspiciousneck'] in [0,1] and v['imgsuspiciousdistantmeta'] in [0,1] and (v['lb_basaltg'] >= 1 or v['lblstimulatedtg'] >= 10 or v['dsevidence'] ==2):
        if debug:
                print('Biochemical Incomplete')
        return 3
    elif v['ncifsuspiciouslympnodespresent'] == 1 or (v['raiuptake']  == 1 or (v['lb_basaltg']>0.2 and v['lb_basaltg']<1) or  (v['lblstimulatedtg']>1 and v['lblstimulatedtg']<10) or v['lbtgab'] == 2):
        if debug:
                print('Indeterminate')
        return 1
    elif v['ncsuspiciouslympnodes'] in [0,1] and v['imgsuspiciousneck'] in [0, 1] and v['imgsuspiciousdistantmeta'] in [0,1] and v['lbtgab'] == 1 and (
                v['lb_basaltg'] < 0.2 or v['lblstimulatedtg'] < 1) :
        if debug:
                print('Excellent')
        return 4

    if debug:
        print('No category at all')
    return -1


def get_response_to_treatment2(p, v, s):
    if v['ncifsuspiciouslympnodespresent'] == 2 or v['imgsuspiciousneck'] == 2 or v[
        'imgsuspiciousdistantmeta'] == 2 or v['raiuptake'] > 2:
        if debug:
            print('Structural incomplete')
        return 2
    elif v['ncsuspiciouslympnodes'] in [0, 1] and v['imgsuspiciousneck'] in [0, 1] and v[
        'imgsuspiciousdistantmeta'] in [0, 1] and (
            v['lb_basaltg'] > 30 or v['dsevidence'] == 2):
        if debug:
            print('Biochemical Incomplete')
        return 3
    elif v['ncifsuspiciouslympnodespresent'] == 1 or v['raiuptake'] == 1 or (v['lb_basaltg'] > 0.2 and v[
        'lb_basaltg'] < 5) or (v['lblstimulatedtg'] > 2 and v['lblstimulatedtg'] < 10) or v['lbtgab'] == 2:
        if debug:
            print('Indeterminate')
        return 1
    elif v['ncsuspiciouslympnodes'] in [0, 1] and v['imgsuspiciousneck'] in [0, 1] and v[
        'imgsuspiciousdistantmeta'] in [0, 1] and v['lbtgab'] == 1 and (
             v['lb_basaltg'] < 0.2 or v['lblstimulatedtg'] < 2):
        if debug:
            print('Excellent')
        return 4

    if debug:
        print('No category at all')
    return -1


def get_response_to_treatment3(p, v, s):
    if v['ncifsuspiciouslympnodespresent'] == 2 or v['imgsuspiciousneck'] == 2 or v[
        'imgsuspiciousdistantmeta'] == 2 or v['raiuptake'] > 2:
        if debug:
                print('Structural incomplete')
        return 2
    elif v['ncsuspiciouslympnodes'] in [0, 1] and v['imgsuspiciousneck'] in [0, 1] and v[
        'imgsuspiciousdistantmeta'] in [0, 1] and (v['dsevidence'] == 2):
        if debug:
                print('Biochemical Incomplete')
        return 3
    elif v['ncifsuspiciouslympnodespresent'] == 1:
        if debug:
                print('Indeterminate')
        return 1
    elif v['ncsuspiciouslympnodes'] in [0, 1] and v['imgsuspiciousneck'] in [0, 1] and v[
        'imgsuspiciousdistantmeta'] in [0, 1] and v['lbtgab'] == 1 and (v['dsevidence'] == 1):
        if debug:
                print('Excellent')
        return 4

    if debug:
        print('No category at all')
    return -1



# NOTA: la procedura lavora su una copia di visits dal momento che apporta delle modifiche permanenti,
# eliminando le visite di volta in volta escluse.
# Tra le informazioni restituite, vi è l'indicazione della data della visita presa come riferimento

def get_rtt(reference_date, visits, s, p, mode):
    global first_exclusion_vis_3

    rtt = -2
    treatment = 0
    p = p.squeeze()
    s = s.squeeze()

    while len(visits.index) > 0:
        # Individuo la visita più vicina alla reference date
        closest_date = min(visits['date'], key=lambda x: abs(x - reference_date))

        # Individuo l'ultima visita precedente three_years_closest, se esistente. Altrimenti, None
        earlier_visits = visits[visits['date'] < closest_date]

        # necessario per il supporto dei criteri di Siena
        if len(earlier_visits.index) > 0:
            closest_date_prev = min(earlier_visits['date'], key=lambda x: abs(x - reference_date))
            prev_v = visits[visits['date'] == closest_date_prev].sample(n=1).squeeze()
            prev_v=visits[visits['date'] == closest_date_prev]
            prev_v=prev_v.loc[prev_v['id'].idxmax()]
        else:
            prev_v = None

        if debug:
            print('reference date (RTT): ' + str(reference_date))
            print('closest date (RTT): ' + str(closest_date))

        if get_month_diff(closest_date, reference_date) > 6:
            closest_date = None
            break


        # Se la visita individuata rientra nel range di date ammissibili, procedo
        v = visits[visits['date'] == closest_date]
        v = v.loc[v['id'].idxmax()]

        # Se la visita non e' stata esclusa per qualche motivo, calcolo rtt
        if v['id'] not in excluded_visit:
            if mode == "roma":
                if s['sgapproach'] in [1, 2, 4] and p['rra'] == 2:
                    rtt = get_response_to_treatment1(row, v, s)
                    treatment = 1
                elif s['sgapproach'] in [1, 2, 4] or  row['two_sgapproach_three'] == True:
                    rtt = get_response_to_treatment2(row, v, s)
                    treatment = 2
                elif s['sgapproach'] == 3:
                    if p['surgery_count'] == 1:
                        if p['rra'] == 1:
                            rtt = get_response_to_treatment3(row, v, s)
                            treatment = 3
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


    return (rtt, treatment, closest_date)

def get_rtt_latest(visits, s, p, mode):
    global first_exclusion_vis_3

    rtt = -2
    treatment = 0
    p = p.squeeze()
    s = s.squeeze()


    while len(visits.index) > 0:

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

        if debug:
            print('closest date (RTT): ' + str(closest_date))
            # print('previous closest date: ' + str(closest_date_prev))

        # Se la visita individuata rientra nel range di date ammissibili, procedo
        v = visits[visits['date'] == closest_date]
        v = v.loc[v['id'].idxmax()]


        # Se la visita non e' stata esclusa per qualche motivo, calcolo rtt
        if v['id'] not in excluded_visit:
            if mode == "roma":
                if s['sgapproach'] in [1, 2, 4] and p['rra'] == 2:
                    rtt = get_response_to_treatment1(row, v, s)
                    treatment = 1
                elif s['sgapproach'] in [1, 2, 4] or row['two_sgapproach_three'] == True:
                    rtt = get_response_to_treatment2(row, v, s)
                    treatment = 2
                elif s['sgapproach'] == 3 and p['surgery_count'] == 1:
                    rtt = get_response_to_treatment3(row, v, s)
                    treatment = 3
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


    return (rtt, treatment)

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

    new_patient=new_patient.fillna(
        {'hilymphnodemetastasisnum': 0, 'hilymphnodemetastasis': 0, 'hiextraextension': 0, 'hylympnodesize': 0,
         'rra': 0})

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

    df = pd.read_csv(patients_path, sep=",", decimal=".", thousands=",", na_values="NA")

    # Rinomina le colonne per farle combaciare con il vecchio schema
    # Ad esempio: record_id -> id
    rename_map = {
        "record_id": "id"
    }

    df.rename(columns=rename_map, inplace=True)

    df["birthdate"] = pd.NaT


    df["age"].fillna(-1, inplace=True)

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
        "hitumoralfoci", "invasionofstrapmuscles","surgery_count", "atarisk"
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
        new_patient = new_patient[new_patient['id'] == filter_on_patient]

    new_patient.rradate.fillna('',inplace=True)
    new_patient.birthdate.fillna('',inplace=True)
#   nel formato v2 le date sono nella forma US
#   new_patient.rradate =new_patient.rradate.apply(lambda x: dateparser.parse(x, languages=['it']))
#   new_patient.birthdate =new_patient.birthdate.apply(lambda x: dateparser.parse(x, languages=['it']))
# new_patient.rradate = new_patient.rradate.apply(lambda x: dateparser.parse(x))

    new_patient["rradate"] = pd.to_datetime(new_patient["rradate"], format="%Y-%m-%d", errors="coerce")

    new_patient=new_patient.fillna(
        {'hilymphnodemetastasisnum': 0, 'hilymphnodemetastasis': 0, 'hiextraextension': 0, 'hylympnodesize': 0,
         'rra': 0})

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
        new_surgery = new_surgery[new_surgery['patient_id'] == filter_on_patient]

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
    df = pd.read_csv(surgeries_path, sep=",", decimal=".", thousands=",")

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
        new_surgery = new_surgery[new_surgery['patient_id'] == filter_on_patient]

    #new_surgery.id=pd.to_numeric(new_surgery.id, downcast='integer')

    # we replace missing values with 0 for all variables except [Laboratory Basal Tg (ng/mL)] AND [Laboratory Stimulated Tg (ng/mL)]
    new_surgery=new_surgery.fillna({'prophylacticcentralneckdissection': 0})
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
                       "ncifsuspiciouslympnodespresent", "imgsuspiciousneck", "imgsuspiciousdistantmeta",
                       "dsevidence", "raiuptake", "lbtgab", "lb_basaltg", "lblstimulatedtg", "lbtgablevels", "trrai",
                       "trsurgery", "trexternalradio", "trother"]

    new_visit["id"] = range(1, len(new_visit) + 1)

    new_visit = new_visit.drop(new_visit[new_visit['patient_id'] == 'Patient_id'].index)
    new_visit=new_visit[pd.to_numeric(new_visit['id'], errors='coerce').notnull()]

    new_visit.patient_id = pd.to_numeric(new_visit.patient_id)

    if filter_on_patient:
        new_visit = new_visit[new_visit['patient_id'] == filter_on_patient]

#    new_visit.date =new_visit.date.apply(lambda x: dateparser.parse(x, languages=['it']))
    new_visit["date"] = pd.to_datetime(new_visit["date"], format="%Y-%m-%d", errors="coerce")

    new_visit['trrai'].replace({1: 0, 2: 1}, regex=True, inplace=True)
    new_visit['trsurgery'].replace({1: 0, 2: 1}, regex=True, inplace=True)
    new_visit['trexternalradio'].replace({1: 0, 2: 1}, regex=True, inplace=True)
    new_visit['trother'].replace({1: 0, 2: 1}, regex=True, inplace=True)
    # NaN are automatically converted to NaT, by means of errors=coerce
#    new_visit['date']=pd.to_datetime(new_visit['date'],errors='coerce')
    new_visit=new_visit.fillna(
        {'ncifsuspiciouslympnodespresent': 0, 'imgsuspiciousneck': 0, 'imgsuspiciousdistantmeta': 0, 'dsevidence': 0,
         'raiuptake': 0, 'lbtgab': 0, 'lb_basaltg': 0, 'lbtgablevels': 0})


#    new_visit.id = pd.to_numeric(new_visit.id, downcast='integer')
    new_visit.ncnormalresidualtissue = pd.to_numeric(new_visit.ncnormalresidualtissue, downcast='integer')
    new_visit.ncsuspiciousresidualtissue = pd.to_numeric(new_visit.ncsuspiciousresidualtissue, downcast='integer')
    new_visit.ncsuspiciouslympnodes = pd.to_numeric(new_visit.ncsuspiciouslympnodes, downcast='integer')
    new_visit.ncifsuspiciouslympnodespresent = pd.to_numeric(new_visit.ncifsuspiciouslympnodespresent, downcast='integer')
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


    v = pd.read_csv(visits_path, sep=",", skiprows=0, decimal=".", thousands=",", dtype=dtype_map)

    rename_map = {
        "record_id": "patient_id",
        "visit_id":"id",
        "visit_date": "date",
        # Attenzione a ncsuspiciouslympnode -> "ncifsuspiciouslympnodespresent"
            "ncifsuspiciouslympnode": "ncifsuspiciouslympnodespresent",
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
        "ncifsuspiciouslympnodespresent",
        "imgsuspiciousneck",
        "imgsuspiciousdistantmeta",
        "dsevidence",
        "raiuptake",
        "lbtgab",
        "lb_basaltg",
        "lblstimulatedtg",
        "lbtgablevels",
        "trrai",
        "trsurgery",
        "trexternalradio",
        "trother"
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
        new_visit = new_visit[new_visit['patient_id'] == filter_on_patient]

    # nel formato v2 le date sono nella forma US
    #new_visit.date =new_visit.date.apply(lambda x: dateparser.parse(x, languages=['it']))
    #new_visit.date = new_visit.date.apply(lambda x: dateparser.parse(x))

    new_visit['trrai'].replace({1: 0, 2: 1}, regex=True, inplace=True)
    new_visit['trsurgery'].replace({1: 0, 2: 1}, regex=True, inplace=True)
    new_visit['trexternalradio'].replace({1: 0, 2: 1}, regex=True, inplace=True)
    new_visit['trother'].replace({1: 0, 2: 1}, regex=True, inplace=True)
    # NaN are automatically converted to NaT, by means of errors=coerce
#    new_visit['date']=pd.to_datetime(new_visit['date'],errors='coerce')
    new_visit=new_visit.fillna(
        {'ncifsuspiciouslympnodespresent': 0, 'imgsuspiciousneck': 0, 'imgsuspiciousdistantmeta': 0, 'dsevidence': 0,
         'raiuptake': 0, 'lbtgab': 0, 'lb_basaltg': 0, 'lbtgablevels': 0})


    new_visit.id = pd.to_numeric(new_visit.id, downcast='integer')
    new_visit.ncnormalresidualtissue = pd.to_numeric(new_visit.ncnormalresidualtissue, downcast='integer')
    new_visit.ncsuspiciousresidualtissue = pd.to_numeric(new_visit.ncsuspiciousresidualtissue, downcast='integer')
    new_visit.ncsuspiciouslympnodes = pd.to_numeric(new_visit.ncsuspiciouslympnodes, downcast='integer')
    new_visit.ncifsuspiciouslympnodespresent = pd.to_numeric(new_visit.ncifsuspiciouslympnodespresent, downcast='integer')
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


print(f'Loading patients from file {patients_path}')
patient = load_patients_v2(patients_path)
print(f'Loading surgeries from file {surgeries_path}')
surgery = load_surgery_v2(surgeries_path)
print(f'Loading visits from file {visits_path}')
visit = load_visits_v2(visits_path)

if filter_on_patient:
    patient=patient[patient['id'] == filter_on_patient]

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

    if mode == "roma":

        # 1.	Carcinoma midollare della tiroide (“Histology cancer type”=2)
        for index, row in patient[patient['hicancertype'] == 2].iterrows():
            initial_exclusion[row['id']] = 1

        # 2.	Carcinoma anaplastico della tiroide (“Histology subtypes” =12)
        # 3.	UMP  (“Histology subtypes”  = 11)
        # 4.	NIFTP (“Histology subtypes” = 14)
        for index, row in patient[patient['hihistologicsubtypes'].isin([11,12,14])].iterrows():
            initial_exclusion[row['id']] = 1

        # 5.	Non noto RRA (“RRA”=0)
        for index, row in patient[patient['rra'] == 0].iterrows():
            initial_exclusion[row['id']] = 1

        # Applicazione criteri di esclusione su visit

        exclusion_criteria1 = 0
        exclusion_criteria2 = 0
        exclusion_criteria3 = 0

        for index, row in visit.iterrows():
            v_id = row['id']
            # 1. Mancante Tireoglobulina [Laboratory Basal Tg (ng/mL) missing AND Laboratory Stimulated Tg (ng/mL) missing]
            if pd.isnull(row['lb_basaltg']) and pd.isnull(row['lblstimulatedtg']):
                excluded_visit[row['id']] = 1
                first_exclusion_vis_1[row['patient_id']] = 1
                exclusion_criteria1 += 1
                continue

            # 2. Mancante anticorpi anti-tireoglobulina [Laboratory TgAb avalable=0]
            if row['lbtgab']==0:
                excluded_visit[row['id']] = 1
                first_exclusion_vis_1[row['patient_id']] = 1
                exclusion_criteria2 += 1
                continue

            # 3. Mancante ecografia [Neck US normal residual tissue=0 OR Neck US suspicious tissue in thyroid bed=0 OR Neck US suspicious lymph nodes=0]
            if row['ncnormalresidualtissue']==0 or row['ncsuspiciousresidualtissue'] == 0 or row['ncsuspiciouslympnodes'] == 0:
                excluded_visit[row['id']] = 1
                first_exclusion_vis_1[row['patient_id']] = 1
                exclusion_criteria3 += 1
                continue


print(f'Exclusion criteria 1:  {exclusion_criteria1}')
print(f'Exclusion criteria 2:  {exclusion_criteria2}')
print(f'Exclusion criteria 3:  {exclusion_criteria3}')

count = (visit['lbtgab'] == 0).sum()

print(f"LBTGAB == 0 {count}")  # Output: 3

p_ata_risk = dict()

if eval_ata_risk:

    ### Pazienti a rischio alto= (una qualsiasi delle seguenti condizioni)
    patient_h_risk = patient.copy()

    #  FTC invasivo (FTC con invasione vascolare) ["Histology subtypes" = 8]
    cond1_h = patient_h_risk['hihistologicsubtypes'] == 8

    #  ["Histology subtypes"= 6, 7, 9 AND "Histology vascular invasion" = 2]
    cond2_h = (patient_h_risk['hihistologicsubtypes'].isin([6, 9])) & (patient_h_risk['hivascolarinvasion'] == 2)

    #  Estensione extratiroidea macroscopica ["Histology extra-thyroid extension" &gt;2]
    cond3_h = patient_h_risk['hiextraextension'].astype(int) > 2

    #  Metastasi linfonodali >=3 cm ["Histology lymph node size" &gt;30 mm]
    cond4_h = patient_h_risk['hylympnodesize'].astype(int) >= 30

    #  Resezione R2 ["Histology surgical margins" = 3]
    cond5_h = patient_h_risk['hysurgicalmargins'] == 3

    # Metastasi alla diagnosi ["M value"=3 OR "M value calculate"=3]
   # cond6_h = (patient_h_risk['satoptm']==3) | (patient_h_risk['forcedm']==3)
    cond6_h = (patient_h_risk['satoptm'] == 3)

    patient_h_risk= patient_h_risk[cond1_h|cond2_h|cond3_h|cond4_h|cond5_h|cond6_h]

    print("Number of high risk patients: " + str(len(patient_h_risk.index)))

    ### Pazienti a rischio intermedio-alto= (una qualsiasi delle seguenti condizioni)
    patient_mh_risk = patient.copy()

    #
    # 1- Istologia aggressiva (PTC variante Tall Cell, scarsamente differenziato, sclerosante;) ["Histology
    # subtypes" = 4, 13]
    cond1_mh = patient_mh_risk['hihistologicsubtypes'].isin([4, 13])

    # 2- Presenza di piu' di 5 metastasi del compartimento centrale ["Histology lymph node metastases" = 3
    # AND "Histology number of metastatic L. nodes" &gt; 5]
    cond2_mh = (patient_mh_risk['hilymphnodemetastasis'] == 3) & (
                patient_mh_risk['hilymphnodemetastasisnum'] > 5)

    # 3- Presenza di metastasi linfonodali nei compartimenti laterocervicali ["Histology lymph node
    # metastases" &gt; 3]
    cond3_mh = patient_mh_risk['hilymphnodemetastasis'].astype(int) > 3

    # 4- PTC con invasione vascolare ["Histology subtypes" = 1,2,3,4,5,10 AND "Histology vascular
    # invasion" = 2]
    cond4_mh = (patient_mh_risk['hihistologicsubtypes'].isin([1, 2, 3, 4, 5, 10])) & (patient_mh_risk[
        'hivascolarinvasion'] == 2)

    patient_mh_risk = patient_mh_risk[(cond1_mh | cond2_mh | cond3_mh | cond4_mh)&(~cond1_h &~cond2_h & ~cond3_h & ~cond4_h & ~cond5_h& ~cond6_h)]

    print("Number of medium high risk patients: " + str(len(patient_mh_risk.index)))


    ### Pazienti a rischio basso-intermedio=
    patient_lm_risk = patient.copy()

    # PTC (eccetto variante Tall Cell, scarsamente differenziato, sclerosante) FTC minimamente invasivo
    # ["Histology subtypes", tutti i valori eccetto 4, 8, 13] AND
    cond1 = ~patient_lm_risk['hihistologicsubtypes'].isin([4, 8, 13])

    # Assenza di invasione vascolare ["Histology vascular invasion" diverso da 2] AND
    cond2 = patient_lm_risk['hivascolarinvasion'] != 2

    # 1- Estensione extratiroidea microscopica ["Histology extra-thyroid extension" =2] OR
    cond3 = patient_lm_risk['hiextraextension'].astype(int) == 2

    # 2- Presenza di massimo 5 metastasi del compartimento centrale ["Histology lymph node metastases" = 3
    # AND "Histology number of metastatic L. nodes" = numero compreso tra 1 e 5]
    cond4 = patient_lm_risk['hilymphnodemetastasis'].astype(int) == 3
    #cond5 = patient_lm_risk['hilymphnodemetastasisnum'].astype(int) > 0
    #cond6 = patient_lm_risk['hilymphnodemetastasisnum'].astype(int) < 6

    cond5 = patient_lm_risk['hilymphnodemetastasisnum'].isna() | (
            (patient_lm_risk['hilymphnodemetastasisnum'].astype(int) >= 0) &
            (patient_lm_risk['hilymphnodemetastasisnum'].astype(int) < 5)
    )
    patient_lm_risk = patient_lm_risk[(cond1 & cond2 & (cond3 | (cond4 & cond5)))&(~cond1_h & ~cond2_h & ~cond3_h & ~cond4_h & ~cond5_h& ~cond6_h)&(~cond1_mh &~cond2_mh &~cond3_mh & ~cond4_mh )]

    print("Number of low_medium risk patients: " + str(len(patient_lm_risk.index)))


    ### Pazienti a rischio basso=
    # PTC (eccetto variante Tall Cell, scarsamente differenziato, sclerosante) FTC minimamente invasivo

    patient_l_risk = patient.copy()
    # ["Histology subtypes" tutti i valori eccetto 4, 8, 13] AND
    #    cond1 = ~patient_l_risk['hihistologicsubtypes'].str.endswith(('.4','.8','.13'))
    cond1 = ~patient_l_risk['hihistologicsubtypes'].isin([4, 8, 13])

    # patient_l_risk = patient_l_risk[~patient_l_risk['hihistologicsubtypes'].str.endswith(('.4','.8','.13'))]

    # Assenza di invasione vascolare ["Histology vascular invasion" diverso da 2] AND
    # patient_l_risk = patient_l_risk[~patient_l_risk['hivascolarinvasion'].str.endswith('.2')]
    cond2 = patient_l_risk['hivascolarinvasion'] != 2

    # Assenza o status metastasi linfonodali sconosciuto ["Histology lymph node metastases" = 1, 2] AND
    # patient_l_risk = patient_l_risk[patient_l_risk['hilymphnodemetastasis'].str.endswith(('1','2'))]
    #cond3 = patient_l_risk['hilymphnodemetastasis'].isin([1, 2])
    # 22/7/2020: Assenza o status metastasi linfonodali sconosciuto [“Histology lymph node metastases” = 0, 1, 2]
    cond3= patient_l_risk['hilymphnodemetastasis'].isin([0, 1, 2])

    # Resezione R0-R1 ["Histology surgical margins" diverso da 3] AND
    # patient_l_risk = patient_l_risk[~patient_l_risk['hysurgicalmargins'].str.endswith('.3')]
    #   cond4 = ~patient_l_risk['hysurgicalmargins'].str.endswith('.3')
    cond4 = patient_l_risk['hysurgicalmargins'].isna() | patient_l_risk['hysurgicalmargins'].isin([0, 1, 2])

    # Estensione extratiroidea assente ["Histology extra-thyroid extension" =1]
    # patient_l_risk = patient_l_risk[patient_l_risk['hiextraextension'].astype(int) == 1]
    cond5 = patient_l_risk['hiextraextension'].astype(int) == 1
    patient_l_risk = patient_l_risk[(cond1 & cond2 & cond3 & cond4 & cond5)&(~cond1_h & ~cond2_h & ~cond3_h & ~cond4_h & ~cond5_h& ~cond6_h)&(~cond1_mh &~cond2_mh &~cond3_mh & ~cond4_mh )]

    print("Number of low risk patients: " + str(len(patient_l_risk.index)))

    pl = set(patient_l_risk['id'].unique())
    plm = set(patient_lm_risk['id'].unique())
    pmh = set(patient_mh_risk['id'].unique())
    ph = set(patient_h_risk['id'].unique())

    p = set(patient['id'].unique())
    p = p - (pl | plm | pmh | ph)

    for p_id in pl:
        p_ata_risk[p_id] = "LOW RISK"

    for p_id in plm:
        p_ata_risk[p_id] = "INTERMEDIATE RISK"

    for p_id in pmh:
        p_ata_risk[p_id] = "INTERMEDIATE RISK"

    for p_id in ph:
        p_ata_risk[p_id] = "HIGH RISK"

    for p_id in p:
        p_ata_risk[p_id] = "UNKNOWN"

    print("Number of unclassified patients: " + str(len(p)))
    if debug:
        print("pl-plm intersection: " + str(pl.intersection(plm)))
        print("pl-pmh intersection: " + str(pl.intersection(pmh)))
        print("pl-ph intersection: " + str(pl.intersection(ph)))
        print("plm-pmh intersection: " + str(plm.intersection(pmh)))
        print("plm-ph intersection: " + str(plm.intersection(ph)))
        print("pmh-ph intersection: " + str(pmh.intersection(ph)))



output_list = []

count = 0
missing_visits_count = 0
missing_surgery_count = 0

# Dato un paziente, quante delle visite ricadono nell'intervallo [6,18]
visits_count_12m = 0

# Dato un paziente, quante delle visite ricadono nell'intervallo [6,18] e non sono filtrate dai criteri di esclusione
included_visits_count_12m = 0

print(f'Processing {len(patient)} patients:')

# For each patient
for p, row in patient.iterrows():
    if use_v2:
        p = row['id']
    else:
        p = int(row['id'])
        birth_date = row['birthdate']

    rradate = row['rradate']
    rra = row['rra']

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
    visits = visit[visit['patient_id'] == p]
    surgeries = surgery[surgery['patient_id'] == p]
    surgery_count = len(surgeries.index)
    # We pre evaluate a condition required for TT alone case during rtt evaluation
    if surgery_count == 2 and len(surgery[surgery['sgapproach']==3].index) == 2:
        row['two_sgapproach_three'] = True
    else:
        row['two_sgapproach_three'] = False
    row['surgery_count'] = surgery_count

    last_surgery_approach = -1
    last_sgcentralcompartmentneckdissection = -1
    last_sglateralcompartmentneckdissection = -1

    if surgery_count>0:
        oldest_date = min(surgeries['sgdateofsurgery'])

        if rra == 2:
            most_recent_date = rradate
            # Se Table Patients, RRA=2; [differenza RRA date [Table Patients] - Visit Date[Table Visits]
            # Se RRA date is null, [differenza date of Surgery[prima occorrenza, Table Surgery] - Visit Date[Table Visits]
            if pd.isnull(most_recent_date):
                most_recent_date = max(surgeries['sgdateofsurgery'])
        elif rra == 1:
            # Se Table Patients, RRA=1; [differenza date of Surgery[prima occorrenza, Table Surgery] - Visit Date[Table Visits]
            most_recent_date = max(surgeries['sgdateofsurgery'])

        # Indepdendently of the value of rra, we also consider as surgery the most recent one
        #        s = surgeries[surgeries['sgdateofsurgery'] == most_recent_date]
        s = surgeries[surgeries['sgdateofsurgery'] == max(surgeries['sgdateofsurgery'])]
        last_surgery_approach = s['sgapproach'].squeeze()
        last_sgcentralcompartmentneckdissection = s['sgcentralcompartmentneckdissection'].squeeze()
        last_sglateralcompartmentneckdissection = s['sglateralcompartmentneckdissection'].squeeze()
        last_prophylacticcentralneckdissection = s['prophylacticcentralneckdissection'].squeeze()

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


    if len(visits.index) == 0:
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

        reference_date = most_recent_date

        # Response 5 years after
        five_years_after = most_recent_date + datetime.timedelta(5 * 365)
        rtt_5y, treatment, reference_date_5y = get_rtt(five_years_after, visits, s, row, mode)

        # Response 3 years after
        three_years_after = most_recent_date + datetime.timedelta(3 * 365)
        rtt_3y, treat, reference_date_3y = get_rtt(three_years_after, visits, s, row, mode)
        if treatment == 0:
            treatment = treat

        # Response 12 months after
        twelve_months_after = most_recent_date + datetime.timedelta(365)
        rtt_12m, treat, reference_date_12m = get_rtt(twelve_months_after, visits, s, row, mode)
        if treatment == 0:
            treatment = treat

        if rtt_12m == -2:
            no6mvisits += 1
        # First 12 months treatments

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
                    print('Included')
                else:
                    print(f"Included but excluded: {cur_v['lbtgab']}")

            else:
                print(f"cur_v {cur_v['date']} 12_months_after {twelve_months_after}")

        # Response latest visit
        rtt_latest, treat = get_rtt_latest(visits, s, row, mode)
        if treatment == 0:
            treatment = treat


    else:
        first_exclusion_vis_3[p] = 1

    record['patient_id'] = p
    record['rtt_5y'] = rtt_5y
    record['rtt_3y'] = rtt_3y
    record['rtt_12m'] = rtt_12m
    record['rtt_latest'] = rtt_latest
    record['ata_risk'] = p_ata_risk[p]
    record['age'] = patient_age
    record['sex'] = row['sex']
    record['tcddiagnosis'] = row['tcddiagnosis']
    record['sgapproach'] = last_surgery_approach
    record['sgcentralcompartmentneckdissection'] = last_sgcentralcompartmentneckdissection
    record['sglateralcompartmentneckdissection'] = last_sglateralcompartmentneckdissection
    record['hihistologicsubtypes'] = row['hihistologicsubtypes']
    record['hitumorsize'] = row['hitumorsize']
    record['hitumoralfoci'] = row['hitumoralfoci']
    record['hiextraextension'] = row['hiextraextension']
    record['invasionofstrapmuscles'] = row['invasionofstrapmuscles']
    record['hilymphnodemetastasis'] = row['hilymphnodemetastasis']
    record['hinumberofremovedlymphnodes'] = row['hinumberofremovedlymphnodes']
    record['clinicalcentre_id'] = row['clinicalcentre_id']
    record['prophylacticcentralneckdissection'] = last_prophylacticcentralneckdissection
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

    output_list.append(record)

print('missing visits count: ' + str(missing_visits_count))
print('missing surgery count: ' + str(missing_surgery_count))

print(f'Saving final report to files: {xls_output_file}, {csv_output_file}')
output = pd.DataFrame(output_list,
                      columns=['patient_id', 'sex', 'age', 'clinicalcentre_id', 'sgapproach', 'tcddiagnosis',
                               'prophylacticcentralneckdissection', 'sgcentralcompartmentneckdissection',
                               'sglateralcompartmentneckdissection', 'hihistologicsubtypes', 'hitumorsize',
                               'hitumoralfoci', 'hiextraextension', 'invasionofstrapmuscles', 'hilymphnodemetastasis',
                               'hinumberofremovedlymphnodes', 'treatment', 'rtt_5y', 'rtt_3y', 'rtt_12m', 'rtt_latest',
                               'ata_risk','external_ata_risk', 'first_exclusion', 'first_exclusion_vis_1', 'first_exclusion_vis_2',
                               'first_exclusion_vis_3', 'missing_visit', 'missing_surgery', 'visits_count_12m',
                               'included_visits_count_12m', 'forcedm', 'satoptm', 'hysurgicalmargins',
                               'rraradioiodineactivity', 'rraradioiodineactivitynum', 'hivascolarinvasion',
                               'treat_012m', 'treat_1236m', 'treat_3660m', 'treat2_012m', 'treat2_1236m',
                               'treat2_3660m','reference_date','reference_date_12m','reference_date_3y','reference_date_5y'])

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