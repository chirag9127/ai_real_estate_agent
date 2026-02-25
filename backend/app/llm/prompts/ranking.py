from __future__ import annotations

RANKING_SYSTEM_PROMPT = """You are a real estate listing evaluation specialist.

You will be given:
1. A list of client requirements (semantic must-haves and nice-to-haves)
2. Multiple property listings with their descriptions and attributes

For each listing, evaluate EVERY semantic must-have and nice-to-have requirement.

You must output ONLY a valid JSON object with this structure:
{
  "listings": {
    "<listing_id>": {
      "must_have_checks": {
        "<must_have_text>": {
          "pass": true/false,
          "reason": "brief explanation"
        }
      },
      "nice_to_have_scores": {
        "<nice_to_have_text>": {
          "score": 0.0 to 1.0,
          "reason": "brief explanation"
        }
      }
    }
  }
}

EVALUATION RULES:
1. For must_have_checks: return true only if the listing clearly satisfies the requirement based on available information. If uncertain, return false.
2. For nice_to_have_scores: 1.0 means perfectly satisfied, 0.5 means partially, 0.0 means not at all. Use 0.3 if information is insufficient to determine.
3. Base evaluations on the listing description, neighborhood, property type, and all available attributes.
4. Be specific in your reasons — reference concrete details from the listing.
5. Return ONLY the JSON object. No markdown, no explanation, no wrapping."""


def build_ranking_user_prompt(
    semantic_must_haves: list[str],
    nice_to_haves: list[str],
    listings: list[dict],
) -> str:
    listings_text = ""
    for listing in listings:
        price = listing.get("price")
        price_str = f"${price:,.0f}" if price else "N/A"
        desc = listing.get("description") or "No description available"
        # Truncate long descriptions to keep prompt manageable
        if len(desc) > 300:
            desc = desc[:297] + "..."

        listings_text += (
            f"\n--- LISTING ID: {listing['id']} ---\n"
            f"Address: {listing.get('address', 'N/A')}\n"
            f"Price: {price_str}\n"
            f"Bedrooms: {listing.get('bedrooms', 'N/A')}\n"
            f"Bathrooms: {listing.get('bathrooms', 'N/A')}\n"
            f"Sqft: {listing.get('sqft', 'N/A')}\n"
            f"Property Type: {listing.get('property_type', 'N/A')}\n"
            f"Neighborhood: {listing.get('neighborhood', 'N/A')}\n"
            f"Year Built: {listing.get('year_built', 'N/A')}\n"
            f"Days on Market: {listing.get('days_on_market', 'N/A')}\n"
            f"Description: {desc}\n"
        )

    must_have_lines = (
        "\n".join(f"- {mh}" for mh in semantic_must_haves)
        if semantic_must_haves
        else "- (none)"
    )
    nice_to_have_lines = (
        "\n".join(f"- {nth}" for nth in nice_to_haves) if nice_to_haves else "- (none)"
    )

    return (
        f"Evaluate the following {len(listings)} listings against these client requirements.\n\n"
        f"SEMANTIC MUST-HAVES (deal-breakers):\n{must_have_lines}\n\n"
        f"NICE-TO-HAVES (preferences):\n{nice_to_have_lines}\n\n"
        f"LISTINGS:\n{listings_text}\n"
        f"Evaluate every listing against every requirement. Return ONLY the JSON object."
    )
