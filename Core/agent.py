import json
import re
import traceback

import requests

from config import (MAX_ERROR_DETAILS, MAX_HISTORY_MESSAGES, MAX_RECOVERY_ATTEMPTS,
                    MAX_TOOL_ROUNDS, MODEL, REQUEST_TIMEOUT, THINK_ENABLED, URL)
from prompts import SYSTEM_PROMPT
from Core.dispatcher import execute_tool, normalize_tool_arguments
from Tools.schemas import tools
from Tools.screen import capture_screen

messages = [{"role": "system", "content": SYSTEM_PROMPT}]
_system_ready = False

def load_modelfile_system():
    """
    Récupère le SYSTEM du Modelfile via /api/show.
    Renvoie "" si le Modelfile n'en a pas, None si Ollama ne répond pas.

    Pourquoi : dès qu'une requête /api/chat contient un message `system`,
    Ollama n'ajoute plus le SYSTEM du Modelfile. Il faut donc le réinjecter.
    """
    try:
        response = requests.post(
            URL.rsplit("/api/", 1)[0] + "/api/show",
            json={"model": MODEL, "name": MODEL},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        print(f"[AVERTISSEMENT] Lecture du Modelfile impossible : {exc}")
        return None

    system = (data.get("system") or "").strip()
    if not system:
        match = re.search(
            r'^SYSTEM\s+("""|\'\'\')(.*?)\1',
            data.get("modelfile") or "",
            re.S | re.M,
        )
        if match:
            system = match.group(2).strip()
    return system
def ensure_system_prompt():
    """Fusionne l'identité du Modelfile et les consignes d'outils (une seule fois)."""
    global _system_ready
    if _system_ready:
        return
    base = load_modelfile_system()
    if base is None:
        return  # Ollama ne répond pas : nouvel essai au prochain message
    messages[0]["content"] = (base + "\n\n" + SYSTEM_PROMPT.strip()) if base else SYSTEM_PROMPT
    _system_ready = True
def stream_chat(on_token=None, on_thinking=None, on_tool=None, on_response_start=None):
    """
    Streaming Ollama robuste pour JARVIS.
    Affiche le texte une seule fois et collecte les tool_calls.
    Fournit des diagnostics détaillés en cas d'erreur HTTP ou JSON.
    """

    payload = {
        "model": MODEL,
        "messages": messages,
        "Tools": tools,
        "stream": True,
        "think": THINK_ENABLED
    }

    content_parts = []
    tool_calls = []
    header_printed = False

    response = None

    try:
        # ==================================================
        # ENVOI DE LA REQUÊTE
        # ==================================================

        response = requests.post(
            URL,
            json=payload,
            stream=True
        )

        # Diagnostic détaillé des erreurs HTTP
        if not response.ok:
            try:
                error_details = response.text
            except Exception:
                error_details = "Impossible de lire le détail de l'erreur."

            print("\n[ERREUR HTTP OLLAMA]")
            print(f"Code : {response.status_code}")
            print(f"Détail : {error_details}")

            response.raise_for_status()

        # ==================================================
        # LECTURE DU STREAM
        # ==================================================

        last_chunk = {}
        thinking_length = 0

        for raw_line in response.iter_lines(decode_unicode=True):

            if not raw_line:
                continue

            if isinstance(raw_line, bytes):
                raw_line = raw_line.decode("utf-8", errors="replace")

            try:
                chunk = json.loads(raw_line)

                last_chunk = chunk
                thinking_length += len(
                    (chunk.get("message") or {}).get("thinking") or ""
                )

            except json.JSONDecodeError as e:
                print("\n[AVERTISSEMENT] Fragment JSON invalide.")
                print(f"Détail : {e}")
                print(f"Contenu : {raw_line[:500]}")
                continue

            # Erreur éventuellement renvoyée par Ollama
            if chunk.get("error"):
                raise RuntimeError(
                    f"Erreur renvoyée par Ollama : {chunk['error']}"
                )

            message_data = chunk.get("message") or {}

            # ==================================================
            # RÉFLEXION DU MODÈLE (si le modèle la fournit)
            # ==================================================

            thinking_token = message_data.get("thinking") or ""
            if thinking_token and on_thinking:
                on_thinking(thinking_token)

            # ==================================================
            # TEXTE GÉNÉRÉ
            # ==================================================

            token = message_data.get("content") or ""
            if token and on_response_start:
                on_response_start()
                on_response_start = None
            if token and on_token:
                on_token(token)

            if token:
                if not header_printed:
                    print("\nJARVIS > ", end="", flush=True)
                    header_printed = True

                print(token, end="", flush=True)
                content_parts.append(token)

            # ==================================================
            # APPELS D'OUTILS
            # ==================================================

            calls = message_data.get("tool_calls") or []

            if calls:
                tool_calls.extend(calls)
                if on_tool:
                    for tool_call in calls:
                        fn = tool_call.get("function") or {}
                        on_tool("Appel demandé", fn.get("name", "outil"), fn.get("arguments", {}))

            # Fin du flux
            if chunk.get("done", False):
                break

        # Vérification de la réponse
        if not content_parts and not tool_calls:
            print("\n[AVERTISSEMENT] Ollama a terminé sans contenu ni outil.")
            print(f"[DIAGNOSTIC] Réflexion reçue : {thinking_length} caractères")
            print(f"[DIAGNOSTIC] done : {last_chunk.get('done')}")
            print(f"[DIAGNOSTIC] done_reason : {last_chunk.get('done_reason')}")
            print(f"[DIAGNOSTIC] eval_count : {last_chunk.get('eval_count')}")

        content = "".join(content_parts)

        if header_printed:
            print()

        return {
            "role": "assistant",
            "content": content,
            **({"tool_calls": tool_calls} if tool_calls else {})
        }

    except requests.exceptions.HTTPError:
        # L'erreur détaillée a déjà été affichée
        raise

    except requests.exceptions.Timeout:
        print("\n[ERREUR] Délai d'attente dépassé pendant la communication avec Ollama.")
        raise

    except requests.exceptions.ConnectionError:
        print("\n[ERREUR] Impossible de joindre Ollama.")
        print("Vérifie que le serveur Ollama est démarré.")
        raise

    except requests.exceptions.RequestException as e:
        print(f"\n[ERREUR RÉSEAU] {type(e).__name__}: {e}")
        raise

    except RuntimeError:
        raise

    except Exception as e:
        print(f"\n[ERREUR STREAM] {type(e).__name__}: {e}")
        raise

    finally:
        if response is not None:
            response.close()
def append_tool_result(call, name, result):
    tool_message = {
        "role": "tool",
        "tool_name": name,
        "content": str(result)
    }
    call_id = call.get("id")
    if call_id:
        tool_message["tool_call_id"] = call_id
    messages.append(tool_message)
def trim_history():
    """Limite la mémoire envoyée à Ollama entre deux demandes utilisateur."""
    global messages
    if len(messages) > MAX_HISTORY_MESSAGES + 1:
        messages = [messages[0]] + messages[-MAX_HISTORY_MESSAGES:]
def ask_jarvis(user_input, user_images=None, callbacks=None):
    callbacks = callbacks or {}
    ensure_system_prompt()
    user_message = {"role": "user", "content": user_input}
    if user_images:
        user_message["images"] = user_images
    messages.append(user_message)

    recovery_attempts = 0

    for round_number in range(1, MAX_TOOL_ROUNDS + 1):

        # ----------------------------------------------------
        # 1. Demande au modèle
        # ----------------------------------------------------

        try:
            assistant_message = stream_chat(
                on_token=callbacks.get("on_token"),
                on_thinking=callbacks.get("on_thinking"),
                on_tool=callbacks.get("on_tool"),
                on_response_start=callbacks.get("on_response_start")
            )
            recovery_attempts = 0

        except Exception as error:
            recovery_attempts += 1

            error_type = type(error).__name__
            error_message = str(error)
            if callbacks.get("on_tool"):
                callbacks["on_tool"]("Erreur système", "Communication Ollama", {
                    "type": error_type,
                    "message": error_message[:MAX_ERROR_DETAILS],
                    "tentative": recovery_attempts,
                    "maximum": MAX_RECOVERY_ATTEMPTS
                })

            print(
                f"\n[RECUPERATION] Erreur de communication ou de génération "
                f"({recovery_attempts}/{MAX_RECOVERY_ATTEMPTS})."
            )

            if recovery_attempts >= MAX_RECOVERY_ATTEMPTS:
                print("[ÉCHEC] Impossible de récupérer la réponse du modèle.")
                print(f"[DÉTAIL] {error_type}: {error_message}")
                break

            # On transmet l'erreur au modèle comme contexte utilisateur.
            messages.append({
                "role": "user",
                "content": (
                    "La génération précédente a échoué.\n"
                    f"Type : {error_type}\n"
                    f"Erreur : {error_message[:MAX_ERROR_DETAILS]}\n\n"
                    "Analyse cette erreur. Essaie de produire une réponse "
                    "valide. Si le format de ta réponse précédente était "
                    "incorrect, corrige-le. Ne prétends pas que l'action "
                    "a été effectuée."
                )
            })

            continue

        messages.append(assistant_message)

        calls = assistant_message.get("tool_calls", [])

        if not calls:
            trim_history()
            return

        print(f"\n[OUTILS] {len(calls)} action(s) demandée(s).")

        # ----------------------------------------------------
        # 2. Exécution des outils
        # ----------------------------------------------------

        for call in calls:
            function_data = call.get("function") or {}
            name = function_data.get("name", "")

            try:
                args = normalize_tool_arguments(
                    function_data.get("arguments", {})
                )

                print(f"\n[ACTION {name}]")

                if name == "capture_screen":
                    screenshot, width, height = capture_screen()

                    append_tool_result(
                        call,
                        name,
                        json.dumps({
                            "success": True,
                            "result": "Capture effectuée.",
                            "width": width,
                            "height": height,
                            "coordinate_system": (
                                "Utiliser les coordonnées de cette image."
                            )
                        }, ensure_ascii=False)
                    )

                    messages.append({
                        "role": "user",
                        "content": (
                            f"Voici la capture récente de l'écran "
                            f"({width}x{height}). Analyse-la pour continuer "
                            "la tâche. Les coordonnées souris doivent "
                            "correspondre à cette image."
                        ),
                        "images": [screenshot]
                    })

                    if callbacks.get("on_tool"):
                        callbacks["on_tool"]("Résultat", name, {
                            "success": True,
                            "result": "Capture effectuée et transmise au modèle.",
                            "dimensions": f"{width}x{height}"
                        })
                    print(f"[VISION] Capture transmise ({width}x{height}).")
                    continue

                result = execute_tool(name, args)
                append_tool_result(call, name, result)
                if callbacks.get("on_tool"):
                    try:
                        parsed_result = json.loads(result) if isinstance(result, str) else result
                    except (TypeError, json.JSONDecodeError):
                        parsed_result = result
                    is_error = isinstance(parsed_result, dict) and parsed_result.get("success") is False
                    callbacks["on_tool"]("Erreur" if is_error else "Résultat", name, parsed_result)

            except Exception as error:
                # Même une erreur de traitement d'arguments est communiquée
                # au modèle afin qu'il puisse corriger son appel.
                error_info = {
                    "success": False,
                    "tool": name,
                    "error_type": type(error).__name__,
                    "error": str(error),
                    "traceback": traceback.format_exc()[-MAX_ERROR_DETAILS:],
                    "instruction": (
                        "Analyse cette erreur et corrige ton appel d'outil."
                    )
                }

                append_tool_result(
                    call,
                    name,
                    json.dumps(error_info, ensure_ascii=False)
                )
                if callbacks.get("on_tool"):
                    callbacks["on_tool"]("Erreur", name, error_info)

                print(
                    f"[ERREUR] {name} — "
                    f"{type(error).__name__}: {error}"
                )

    limit_details = (
        f"JARVIS a atteint la limite de {MAX_TOOL_ROUNDS} cycles d'outils "
        f"ou de {MAX_RECOVERY_ATTEMPTS} tentatives de récupération."
    )
    print("\n[LIMITE] " + limit_details)
    if callbacks.get("on_tool"):
        callbacks["on_tool"]("Limite système", "Exécution", limit_details)

    messages.append({
        "role": "assistant",
        "content": (
            "Je n'ai pas pu terminer cette tâche. "
            "Une erreur technique ou une limite d'exécution m'a bloqué."
        )
    })

    trim_history()
