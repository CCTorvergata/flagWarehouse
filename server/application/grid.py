# server/application/grid.py

from flask import (
    Blueprint, render_template, request
)
import requests
from .db import get_db

bp = Blueprint('grid', __name__)

# Paletta di colori per i servizi. Aggiungine altri se hai molti servizi.
SERVICE_COLORS_PALETTE = [
    '#dc3545', '#28a745', '#007bff', '#ffc107', '#17a2b8', '#6f42c1',
    '#fd7e14', '#20c997', '#6610f2', '#e83e8c'
]

@bp.route('/grid')
def show_grid():
    """
    Mostra una griglia filtrabile per servizio.
    Le celle indicano con colori diversi le flag catturate per ogni servizio.
    """
    db = get_db()
    
    # Recupera i nomi dei team e dei servizi dall'API
    team_names = {}
    service_names = {}
    try:
        response = requests.get('http://10.10.0.1/api/status', timeout=5)
        if response.status_code == 200:
            api_data = response.json()
            team_names = {team['id']: team['name'] for team in api_data.get('teams', [])}
            # Usa 'vulnboxId' come chiave per i servizi, come da output dell'API
            service_names = {i: service['name'] for i, service in enumerate(api_data.get('services', []))}
    except requests.exceptions.RequestException as e:
        # In caso di errore, la griglia verrà mostrata con i nomi di default
        print(f"Could not fetch data from status API: {e}")

    # Considera solo le flag delle ultime 12 ore
    query = "SELECT flag FROM flags WHERE time >= datetime('now', '-12 hours')"
    flags = db.execute(query).fetchall()
    
    # Struttura dati: {(round, team_id): {service_id_1, service_id_2}}
    found_flags_by_service = {}
    teams_data = {}
    all_services = set()
    max_round = 0

    for row in flags:
        flag_str = row['flag']
        if len(flag_str) >= 6: # La flag deve contenere anche l'ID servizio
            try:
                round_num = int(flag_str[0:2], 36)
                team_num = int(flag_str[2:4], 36)
                service_num = int(flag_str[4:6], 36)
                
                # Popola la struttura dati
                cell_data = found_flags_by_service.setdefault((round_num, team_num), set())
                cell_data.add(service_num)
                
                all_services.add(service_num)
                
                if round_num > max_round:
                    max_round = round_num

                if team_num not in teams_data:
                    # Usa il nome del team dall'API, con un fallback
                    team_name = team_names.get(team_num, f'Team {team_num}')
                    teams_data[team_num] = {'id': team_num, 'name': team_name}

            except (ValueError, IndexError):
                pass

    # Gestione filtri dal form
    selected_services_str = request.args.getlist('service')
    if selected_services_str:
        selected_services = {int(s) for s in selected_services_str}
    else:
        # Se nessun servizio è selezionato, mostrali tutti
        selected_services = all_services

    # Assegna un colore a ogni ID di servizio
    sorted_services = sorted(list(all_services))
    service_colors = {
        service_id: SERVICE_COLORS_PALETTE[i % len(SERVICE_COLORS_PALETTE)]
        for i, service_id in enumerate(sorted_services)
    }

    teams = sorted(teams_data.values(), key=lambda t: t['id'])
    rounds = range(1, max_round + 1)

    return render_template(
        'grid.html',
        teams=teams,
        rounds=rounds,
        found_flags_by_service=found_flags_by_service,
        all_services=sorted_services,
        selected_services=selected_services,
        service_colors=service_colors,
        service_names=service_names  # Passa i nomi dei servizi al template
    )