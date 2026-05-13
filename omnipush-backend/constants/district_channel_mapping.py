"""
District to Channel Group Mapping

Maps Tamil Nadu district names (in Tamil and English) to their corresponding channel group names.
This mapping is used for auto-suggesting channel groups when publishing news items
from external sources (like NewsIt) that include district information.

Usage: When a news item has district information, the system will automatically
suggest and pre-select the corresponding channel group in the publish dialog.
"""

from typing import Dict, Optional


# Tamil Nadu District to Channel Group Name Mapping
# Key: District name in Tamil or English (as received from NewsIt)
# Value: Corresponding channel group name
DISTRICT_CHANNEL_MAPPING: Dict[str, str] = {
    # Major Cities
    'சென்னை': 'Chennai_Channels_Group',
    'Chennai': 'Chennai_Channels_Group',

    'கோயம்புத்தூர்': 'Coimbatore_Channels_Group',
    'Coimbatore': 'Coimbatore_Channels_Group',

    'மதுரை': 'Madurai_Channels_Group',
    'Madurai': 'Madurai_Channels_Group',

    'திருச்சிராப்பள்ளி': 'Trichy_Channels_Group',
    'Tiruchirappalli': 'Trichy_Channels_Group',
    'Trichy': 'Trichy_Channels_Group',

    'சேலம்': 'Salem_Channels_Group',
    'Salem': 'Salem_Channels_Group',

    'திருநெல்வேலி': 'Tirunelveli_Channels_Group',
    'Tirunelveli': 'Tirunelveli_Channels_Group',

    # Districts (Alphabetical by Tamil name)
    'அரியலூர்': 'Ariyalur_Channels_Group',
    'Ariyalur': 'Ariyalur_Channels_Group',

    'கடலூர்': 'Cuddalore_Channels_Group',
    'Cuddalore': 'Cuddalore_Channels_Group',

    'தஞ்சாவூர்': 'Thanjavur_Channels_Group',
    'Thanjavur': 'Thanjavur_Channels_Group',

    'தர்மபுரி': 'Dharmapuri_Channels_Group',
    'Dharmapuri': 'Dharmapuri_Channels_Group',

    'திண்டுக்கல்': 'Dindigul_Channels_Group',
    'Dindigul': 'Dindigul_Channels_Group',

    'ஈரோடு': 'Erode_Channels_Group',
    'Erode': 'Erode_Channels_Group',

    'காஞ்சிபுரம்': 'Kanchipuram_Channels_Group',
    'Kanchipuram': 'Kanchipuram_Channels_Group',

    'கன்னியாகுமரி': 'Kanyakumari_Channels_Group',
    'Kanyakumari': 'Kanyakumari_Channels_Group',

    'கரூர்': 'Karur_Channels_Group',
    'Karur': 'Karur_Channels_Group',

    'கிருஷ்ணகிரி': 'Krishnagiri_Channels_Group',
    'Krishnagiri': 'Krishnagiri_Channels_Group',

    'நாகப்பட்டினம்': 'Nagapattinam_Channels_Group',
    'Nagapattinam': 'Nagapattinam_Channels_Group',

    'நாமக்கல்': 'Namakkal_Channels_Group',
    'Namakkal': 'Namakkal_Channels_Group',

    'நீலகிரி': 'Nilgiris_Channels_Group',
    'Nilgiris': 'Nilgiris_Channels_Group',
    'The Nilgiris': 'Nilgiris_Channels_Group',

    'பெரம்பலூர்': 'Perambalur_Channels_Group',
    'Perambalur': 'Perambalur_Channels_Group',

    'புதுக்கோட்டை': 'Pudukkottai_Channels_Group',
    'Pudukkottai': 'Pudukkottai_Channels_Group',

    'இராமநாதபுரம்': 'Ramanathapuram_Channels_Group',
    'Ramanathapuram': 'Ramanathapuram_Channels_Group',

    'ரானிப்பேட்டை': 'Ranipet_Channels_Group',
    'Ranipet': 'Ranipet_Channels_Group',

    'சிவகங்கை': 'Sivaganga_Channels_Group',
    'Sivaganga': 'Sivaganga_Channels_Group',

    'தென்காசி': 'Tenkasi_Channels_Group',
    'Tenkasi': 'Tenkasi_Channels_Group',

    'திருவண்ணாமலை': 'Tiruvannamalai_Channels_Group',
    'Tiruvannamalai': 'Tiruvannamalai_Channels_Group',

    'திருவாரூர்': 'Tiruvarur_Channels_Group',
    'Tiruvarur': 'Tiruvarur_Channels_Group',

    'தூத்துக்குடி': 'Thoothukudi_Channels_Group',
    'Thoothukudi': 'Thoothukudi_Channels_Group',
    'Tuticorin': 'Thoothukudi_Channels_Group',

    'திருப்பூர்': 'Tiruppur_Channels_Group',
    'Tiruppur': 'Tiruppur_Channels_Group',

    'திருப்பத்தூர்': 'Tirupattur_Channels_Group',
    'Tirupattur': 'Tirupattur_Channels_Group',

    'திருவள்ளூர்': 'Tiruvallur_Channels_Group',
    'Tiruvallur': 'Tiruvallur_Channels_Group',

    'வேலூர்': 'Vellore_Channels_Group',
    'Vellore': 'Vellore_Channels_Group',

    'விழுப்புரம்': 'Viluppuram_Channels_Group',
    'Viluppuram': 'Viluppuram_Channels_Group',

    'விருதுநகர்': 'Virudhunagar_Channels_Group',
    'Virudhunagar': 'Virudhunagar_Channels_Group',

    # Newly formed districts
    'சேங்கல்பட்டு': 'Chengalpattu_Channels_Group',
    'Chengalpattu': 'Chengalpattu_Channels_Group',

    'கள்ளக்குறிச்சி': 'Kallakurichi_Channels_Group',
    'Kallakurichi': 'Kallakurichi_Channels_Group',

    'மயிலாடுதுறை': 'Mayiladuthurai_Channels_Group',
    'Mayiladuthurai': 'Mayiladuthurai_Channels_Group',

    # Fallback for generic/state-level news
    'தமிழ்நாடு': 'TamilNadu_General_Channels_Group',
    'Tamil Nadu': 'TamilNadu_General_Channels_Group',
    'TN': 'TamilNadu_General_Channels_Group',
}


def get_suggested_channel_group_name(district: Optional[str]) -> Optional[str]:
    """
    Get suggested channel group name for a given district

    Args:
        district: District name (in Tamil or English)

    Returns:
        Suggested channel group name, or None if no mapping exists
    """
    if not district or not isinstance(district, str):
        return None

    # Trim and normalize the district name
    normalized_district = district.strip()

    # Look up in mapping (case-sensitive to handle Tamil characters properly)
    return DISTRICT_CHANNEL_MAPPING.get(normalized_district)
