# The issue is in the paperless_ngx_documents route - the return statement is incorrectly indented
# Here's the corrected version of that specific route:

@web.route("/paperless-ngx-documents")
def paperless_ngx_documents():
    paperless_ngx_docs = []
    current_page = request.args.get("page", 1, type=int)
    search_query = request.args.get("q", "", type=str)
    per_page = 10  # Default items per page for Paperless-ngx

    # Retrieve configuration from the 'config' object passed to the blueprint
    PAPERLESS_NGX_BASE_URL = config.get("paperless", "api_url", fallback="")
    PAPERLESS_NGX_API_TOKEN = config.get("paperless", "api_token", fallback="")

    # Initialize pagination data
    pagination = {
        "page": current_page,
        "per_page": per_page,
        "total": 0,
        "pages": 0,
        "has_prev": False,
        "has_next": False,
        "prev_num": None,
        "next_num": None,
        "iter_pages": lambda: [],
    }

    if not PAPERLESS_NGX_BASE_URL:
        flash(
            "Paperless-ngx Base URL is not configured. Please set it in Configuration.",
            "error",
        )
        logger.error("Paperless-ngx Base URL not configured.")
        return render_template(
            "paperless_ngx_documents.html",
            paperless_ngx_docs=paperless_ngx_docs,
            pagination=pagination,
            YOUR_PAPERLESS_NGX_URL="#",  # Fallback for template
            YOUR_PAPERLESS_NGX_BASE_URL="#",
        )

    if not PAPERLESS_NGX_API_TOKEN:
        flash(
            "Paperless-ngx API Token is not configured. Please set it in Configuration.",
            "error",
        )
        logger.error("Paperless-ngx API Token not configured.")
        return render_template(
            "paperless_ngx_documents.html",
            paperless_ngx_docs=paperless_ngx_docs,
            pagination=pagination,
            YOUR_PAPERLESS_NGX_URL=PAPERLESS_NGX_BASE_URL,
            YOUR_PAPERLESS_NGX_BASE_URL=PAPERLESS_NGX_BASE_URL,
        )

    headers = {
        "Authorization": f"Token {PAPERLESS_NGX_API_TOKEN}",
    }

    params = {
        "page": current_page,
        "page_size": per_page,
        "order_by": "-created",  # Sort by creation date, newest first
    }
    if search_query:
        params["query"] = search_query  # Pass search query to Paperless-ngx API

    try:
        api_url = f"{PAPERLESS_NGX_BASE_URL}documents/"
        logger.info(
            f"Fetching Paperless-ngx documents from: {api_url} with params: {params}"
        )

        # It's highly recommended to set verify=True and provide a CA bundle
        # or ensure your Paperless-ngx has a valid certificate in production.
        # For local development, verify=False might be used.
        response = requests.get(
            api_url, headers=headers, params=params, verify=False
        )
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
        data = response.json()

        # Prepare mappings for related fields (Correspondents, Document Types, Tags)
        # It's more efficient to fetch these once and cache them if performance is critical
        correspondents_map = {}
        doc_types_map = {}
        tags_map = {}

        # Fetch all correspondents
        try:
            corr_res = requests.get(
                f"{PAPERLESS_NGX_BASE_URL}correspondents/?page_size=max",
                headers=headers,
                verify=False,
            )
            corr_res.raise_for_status()
            for c in corr_res.json().get("results", []):
                correspondents_map[c["id"]] = c["name"]
        except requests.exceptions.RequestException as e:
            logger.warning(f"Could not fetch all correspondents: {e}")

        # Fetch all document types
        try:
            type_res = requests.get(
                f"{PAPERLESS_NGX_BASE_URL}document_types/?page_size=max",
                headers=headers,
                verify=False,
            )
            type_res.raise_for_status()
            for t in type_res.json().get("results", []):
                doc_types_map[t["id"]] = t["name"]
        except requests.exceptions.RequestException as e:
            logger.warning(f"Could not fetch all document types: {e}")

        # Fetch all tags
        try:
            tags_res = requests.get(
                f"{PAPERLESS_NGX_BASE_URL}/tags/?page_size=max",
                headers=headers,
                verify=False,
            )
            tags_res.raise_for_status()
            for t in tags_res.json().get("results", []):
                tags_map[t["id"]] = t["name"]
        except requests.exceptions.RequestException as e:
            logger.warning(f"Could not fetch all tags: {e}")

        for doc in data.get("results", []):
            correspondent_name = correspondents_map.get(
                doc.get("correspondent"), "N/A"
            )
            document_type_name = doc_types_map.get(doc.get("document_type"), "N/A")
            tags_names = [
                tags_map.get(tag_id, "N/A") for tag_id in doc.get("tags", [])
            ]

            paperless_ngx_docs.append(
                {
                    "id": doc.get("id"),
                    "title": doc.get("title", "No Title"),
                    "document_type": document_type_name,
                    "created": doc.get("created"),
                    "correspondent": correspondent_name,
                    "tags": tags_names,
                }
            )

        total_docs = data.get("count", 0)

        # Update pagination details based on API response
        pagination["total"] = total_docs
        pagination["pages"] = (total_docs + per_page - 1) // per_page
        pagination["has_prev"] = data.get("previous") is not None
        pagination["has_next"] = data.get("next") is not None
        pagination["prev_num"] = current_page - 1 if data.get("previous") else None
        pagination["next_num"] = current_page + 1 if data.get("next") else None

        # Simple iter_pages for Jinja2 (consider more robust for large number of pages)
        pagination["iter_pages"] = lambda: range(1, pagination["pages"] + 1)

        logger.info(
            f"Successfully fetched {len(paperless_ngx_docs)} Paperless-ngx documents. Total: {total_docs}"
        )

    except requests.exceptions.RequestException as e:
        flash(
            f"Error connecting to Paperless-ngx API: {e}. Check URL/Token and connectivity.",
            "error",
        )
        logger.error(f"Error connecting to Paperless-ngx API: {e}")
    except KeyError as e:
        flash(
            f"Error parsing Paperless-ngx API response: Missing expected key {e}.",
            "error",
        )
        logger.error(f"Error parsing Paperless-ngx API response: Missing key {e}")
    except Exception as e:
        flash(
            f"An unexpected error occurred while fetching Paperless-ngx documents: {e}",
            "error",
        )
        logger.exception(
            "An unexpected error occurred in paperless_ngx_documents route."
        )  # Use exception for full traceback

    # Clean the base URL to prevent double slashes
    paperless_base_url = PAPERLESS_NGX_BASE_URL.rstrip("/")

    # THIS RETURN STATEMENT NEEDS TO BE PROPERLY INDENTED INSIDE THE FUNCTION
    return render_template(
        "paperless_ngx_documents.html",
        paperless_ngx_docs=paperless_ngx_docs,
        pagination=pagination,
        YOUR_PAPERLESS_NGX_URL=PAPERLESS_NGX_BASE_URL,
        YOUR_PAPERLESS_NGX_BASE_URL=paperless_base_url,  # Pass cleaned URL
        search_query=search_query,
    )
