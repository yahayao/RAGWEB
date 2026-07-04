<template>
  <div class="modal-overlay" @click.self="$emit('cancelled')">
    <div class="modal-box geo-modal-box">
      <!-- Step 1: 国内/海外选择 -->
      <template v-if="step === 1">
        <div class="modal-title">📍 选择您所在的地区</div>
        <p class="modal-desc">未能自动识别您的位置，请手动选择以获取更精准的招生信息。</p>
        <div class="geo-options">
          <button class="geo-option-btn" @click="selectDomestic">
            <span class="geo-option-icon">🇨🇳</span>
            <span class="geo-option-label">国内（含港澳台）</span>
          </button>
          <button class="geo-option-btn" @click="selectOverseas">
            <span class="geo-option-icon">🌍</span>
            <span class="geo-option-label">海外</span>
          </button>
        </div>
        <div class="modal-actions">
          <button class="modal-cancel-btn" @click="$emit('cancelled')">跳过</button>
        </div>
      </template>

      <!-- Step 2: 国内省份选择 -->
      <template v-if="step === 2 && region === 'domestic'">
        <div class="modal-title">📍 选择您的省份</div>
        <p class="modal-desc">请选择您所在的省份或地区。</p>
        <select
          v-model="selectedProvince"
          class="modal-input geo-select"
          size="10"
        >
          <option value="" disabled>-- 请选择 --</option>
          <option
            v-for="p in domesticOptions"
            :key="p.code"
            :value="p.code"
          >{{ p.label }}</option>
        </select>
        <div class="modal-actions">
          <button class="modal-cancel-btn" @click="step = 1">返回</button>
          <button
            class="modal-confirm-btn"
            :disabled="!selectedProvince"
            @click="confirmDomestic"
          >确认</button>
        </div>
      </template>

      <!-- Step 2: 海外国家选择 -->
      <template v-if="step === 2 && region === 'overseas'">
        <div class="modal-title">🌍 选择您的国家/地区</div>
        <p class="modal-desc">请选择您所在的国家或地区。</p>
        <select
          v-model="selectedCountry"
          class="modal-input geo-select"
          size="12"
        >
          <option value="" disabled>-- Select Country --</option>
          <option
            v-for="c in overseasOptions"
            :key="c.code"
            :value="c.code"
          >{{ c.label }}</option>
        </select>
        <div class="modal-actions">
          <button class="modal-cancel-btn" @click="step = 1">返回</button>
          <button
            class="modal-confirm-btn"
            :disabled="!selectedCountry"
            @click="confirmOverseas"
          >确认</button>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useChatStore } from '../store/chat'
import { updateUserGeo } from '../api/chat'

const props = defineProps<{
  userId: string
}>()

const emit = defineEmits<{
  confirmed: []
  cancelled: []
}>()

const chatStore = useChatStore()

// States
const step = ref(1)
const region = ref<'domestic' | 'overseas' | null>(null)
const selectedProvince = ref('')
const selectedCountry = ref('')

// ==================== Domestic Options ====================
interface GeoOption {
  code: string
  label: string
}

const domesticOptions: GeoOption[] = [
  // 31 provinces from CN_PROVINCE_MAP
  { code: 'AH', label: '安徽省' },
  { code: 'BJ', label: '北京市' },
  { code: 'CQ', label: '重庆市' },
  { code: 'FJ', label: '福建省' },
  { code: 'GS', label: '甘肃省' },
  { code: 'GD', label: '广东省' },
  { code: 'GX', label: '广西壮族自治区' },
  { code: 'GZ', label: '贵州省' },
  { code: 'HI', label: '海南省' },
  { code: 'HE', label: '河北省' },
  { code: 'HL', label: '黑龙江省' },
  { code: 'HA', label: '河南省' },
  { code: 'HB', label: '湖北省' },
  { code: 'HN', label: '湖南省' },
  { code: 'JS', label: '江苏省' },
  { code: 'JX', label: '江西省' },
  { code: 'JL', label: '吉林省' },
  { code: 'LN', label: '辽宁省' },
  { code: 'NM', label: '内蒙古自治区' },
  { code: 'NX', label: '宁夏回族自治区' },
  { code: 'QH', label: '青海省' },
  { code: 'SN', label: '陕西省' },
  { code: 'SD', label: '山东省' },
  { code: 'SH', label: '上海市' },
  { code: 'SX', label: '山西省' },
  { code: 'SC', label: '四川省' },
  { code: 'TJ', label: '天津市' },
  { code: 'XZ', label: '西藏自治区' },
  { code: 'XJ', label: '新疆维吾尔自治区' },
  { code: 'YN', label: '云南省' },
  { code: 'ZJ', label: '浙江省' },
  // Special regions
  { code: 'HK', label: '香港特别行政区' },
  { code: 'MO', label: '澳门特别行政区' },
  { code: 'TW', label: '台湾省' },
]

// Province code → name map
const provinceNameMap: Record<string, string> = {}
domesticOptions.forEach((p) => {
  provinceNameMap[p.code] = p.label
})

// Province code → country info for HK/MO/TW
const provinceCountryMap: Record<string, { code: string; name: string }> = {
  HK: { code: 'HK', name: '中国香港' },
  MO: { code: 'MO', name: '中国澳门' },
  TW: { code: 'TW', name: '中国台湾' },
}

// ==================== Overseas Options ====================
// Full ISO 3166-1 country list, English names, sorted alphabetically
const overseasOptions: GeoOption[] = [
  { code: 'AF', label: 'Afghanistan (AF)' },
  { code: 'AX', label: 'Åland Islands (AX)' },
  { code: 'AL', label: 'Albania (AL)' },
  { code: 'DZ', label: 'Algeria (DZ)' },
  { code: 'AS', label: 'American Samoa (AS)' },
  { code: 'AD', label: 'Andorra (AD)' },
  { code: 'AO', label: 'Angola (AO)' },
  { code: 'AI', label: 'Anguilla (AI)' },
  { code: 'AQ', label: 'Antarctica (AQ)' },
  { code: 'AG', label: 'Antigua and Barbuda (AG)' },
  { code: 'AR', label: 'Argentina (AR)' },
  { code: 'AM', label: 'Armenia (AM)' },
  { code: 'AW', label: 'Aruba (AW)' },
  { code: 'AU', label: 'Australia (AU)' },
  { code: 'AT', label: 'Austria (AT)' },
  { code: 'AZ', label: 'Azerbaijan (AZ)' },
  { code: 'BS', label: 'Bahamas (BS)' },
  { code: 'BH', label: 'Bahrain (BH)' },
  { code: 'BD', label: 'Bangladesh (BD)' },
  { code: 'BB', label: 'Barbados (BB)' },
  { code: 'BY', label: 'Belarus (BY)' },
  { code: 'BE', label: 'Belgium (BE)' },
  { code: 'BZ', label: 'Belize (BZ)' },
  { code: 'BJ', label: 'Benin (BJ)' },
  { code: 'BM', label: 'Bermuda (BM)' },
  { code: 'BT', label: 'Bhutan (BT)' },
  { code: 'BO', label: 'Bolivia (BO)' },
  { code: 'BQ', label: 'Bonaire, Sint Eustatius and Saba (BQ)' },
  { code: 'BA', label: 'Bosnia and Herzegovina (BA)' },
  { code: 'BW', label: 'Botswana (BW)' },
  { code: 'BV', label: 'Bouvet Island (BV)' },
  { code: 'BR', label: 'Brazil (BR)' },
  { code: 'IO', label: 'British Indian Ocean Territory (IO)' },
  { code: 'BN', label: 'Brunei Darussalam (BN)' },
  { code: 'BG', label: 'Bulgaria (BG)' },
  { code: 'BF', label: 'Burkina Faso (BF)' },
  { code: 'BI', label: 'Burundi (BI)' },
  { code: 'CV', label: 'Cabo Verde (CV)' },
  { code: 'KH', label: 'Cambodia (KH)' },
  { code: 'CM', label: 'Cameroon (CM)' },
  { code: 'CA', label: 'Canada (CA)' },
  { code: 'KY', label: 'Cayman Islands (KY)' },
  { code: 'CF', label: 'Central African Republic (CF)' },
  { code: 'TD', label: 'Chad (TD)' },
  { code: 'CL', label: 'Chile (CL)' },
  { code: 'CO', label: 'Colombia (CO)' },
  { code: 'KM', label: 'Comoros (KM)' },
  { code: 'CG', label: 'Congo (CG)' },
  { code: 'CD', label: 'Congo, Democratic Republic of the (CD)' },
  { code: 'CK', label: 'Cook Islands (CK)' },
  { code: 'CR', label: 'Costa Rica (CR)' },
  { code: 'CI', label: "Côte d'Ivoire (CI)" },
  { code: 'HR', label: 'Croatia (HR)' },
  { code: 'CU', label: 'Cuba (CU)' },
  { code: 'CW', label: 'Curaçao (CW)' },
  { code: 'CY', label: 'Cyprus (CY)' },
  { code: 'CZ', label: 'Czechia (CZ)' },
  { code: 'DK', label: 'Denmark (DK)' },
  { code: 'DJ', label: 'Djibouti (DJ)' },
  { code: 'DM', label: 'Dominica (DM)' },
  { code: 'DO', label: 'Dominican Republic (DO)' },
  { code: 'EC', label: 'Ecuador (EC)' },
  { code: 'EG', label: 'Egypt (EG)' },
  { code: 'SV', label: 'El Salvador (SV)' },
  { code: 'GQ', label: 'Equatorial Guinea (GQ)' },
  { code: 'ER', label: 'Eritrea (ER)' },
  { code: 'EE', label: 'Estonia (EE)' },
  { code: 'SZ', label: 'Eswatini (SZ)' },
  { code: 'ET', label: 'Ethiopia (ET)' },
  { code: 'FK', label: 'Falkland Islands (Malvinas) (FK)' },
  { code: 'FO', label: 'Faroe Islands (FO)' },
  { code: 'FJ', label: 'Fiji (FJ)' },
  { code: 'FI', label: 'Finland (FI)' },
  { code: 'FR', label: 'France (FR)' },
  { code: 'GF', label: 'French Guiana (GF)' },
  { code: 'PF', label: 'French Polynesia (PF)' },
  { code: 'TF', label: 'French Southern Territories (TF)' },
  { code: 'GA', label: 'Gabon (GA)' },
  { code: 'GM', label: 'Gambia (GM)' },
  { code: 'GE', label: 'Georgia (GE)' },
  { code: 'DE', label: 'Germany (DE)' },
  { code: 'GH', label: 'Ghana (GH)' },
  { code: 'GI', label: 'Gibraltar (GI)' },
  { code: 'GR', label: 'Greece (GR)' },
  { code: 'GL', label: 'Greenland (GL)' },
  { code: 'GD', label: 'Grenada (GD)' },
  { code: 'GP', label: 'Guadeloupe (GP)' },
  { code: 'GU', label: 'Guam (GU)' },
  { code: 'GT', label: 'Guatemala (GT)' },
  { code: 'GG', label: 'Guernsey (GG)' },
  { code: 'GN', label: 'Guinea (GN)' },
  { code: 'GW', label: 'Guinea-Bissau (GW)' },
  { code: 'GY', label: 'Guyana (GY)' },
  { code: 'HT', label: 'Haiti (HT)' },
  { code: 'HM', label: 'Heard Island and McDonald Islands (HM)' },
  { code: 'VA', label: 'Holy See (VA)' },
  { code: 'HN', label: 'Honduras (HN)' },
  { code: 'HU', label: 'Hungary (HU)' },
  { code: 'IS', label: 'Iceland (IS)' },
  { code: 'IN', label: 'India (IN)' },
  { code: 'ID', label: 'Indonesia (ID)' },
  { code: 'IR', label: 'Iran (IR)' },
  { code: 'IQ', label: 'Iraq (IQ)' },
  { code: 'IE', label: 'Ireland (IE)' },
  { code: 'IM', label: 'Isle of Man (IM)' },
  { code: 'IL', label: 'Israel (IL)' },
  { code: 'IT', label: 'Italy (IT)' },
  { code: 'JM', label: 'Jamaica (JM)' },
  { code: 'JP', label: 'Japan (JP)' },
  { code: 'JE', label: 'Jersey (JE)' },
  { code: 'JO', label: 'Jordan (JO)' },
  { code: 'KZ', label: 'Kazakhstan (KZ)' },
  { code: 'KE', label: 'Kenya (KE)' },
  { code: 'KI', label: 'Kiribati (KI)' },
  { code: 'KP', label: "Korea, Democratic People's Republic of (KP)" },
  { code: 'KR', label: 'Korea, Republic of (KR)' },
  { code: 'KW', label: 'Kuwait (KW)' },
  { code: 'KG', label: 'Kyrgyzstan (KG)' },
  { code: 'LA', label: "Lao People's Democratic Republic (LA)" },
  { code: 'LV', label: 'Latvia (LV)' },
  { code: 'LB', label: 'Lebanon (LB)' },
  { code: 'LS', label: 'Lesotho (LS)' },
  { code: 'LR', label: 'Liberia (LR)' },
  { code: 'LY', label: 'Libya (LY)' },
  { code: 'LI', label: 'Liechtenstein (LI)' },
  { code: 'LT', label: 'Lithuania (LT)' },
  { code: 'LU', label: 'Luxembourg (LU)' },
  { code: 'MG', label: 'Madagascar (MG)' },
  { code: 'MW', label: 'Malawi (MW)' },
  { code: 'MY', label: 'Malaysia (MY)' },
  { code: 'MV', label: 'Maldives (MV)' },
  { code: 'ML', label: 'Mali (ML)' },
  { code: 'MT', label: 'Malta (MT)' },
  { code: 'MH', label: 'Marshall Islands (MH)' },
  { code: 'MQ', label: 'Martinique (MQ)' },
  { code: 'MR', label: 'Mauritania (MR)' },
  { code: 'MU', label: 'Mauritius (MU)' },
  { code: 'YT', label: 'Mayotte (YT)' },
  { code: 'MX', label: 'Mexico (MX)' },
  { code: 'FM', label: 'Micronesia (FM)' },
  { code: 'MD', label: 'Moldova (MD)' },
  { code: 'MC', label: 'Monaco (MC)' },
  { code: 'MN', label: 'Mongolia (MN)' },
  { code: 'ME', label: 'Montenegro (ME)' },
  { code: 'MS', label: 'Montserrat (MS)' },
  { code: 'MA', label: 'Morocco (MA)' },
  { code: 'MZ', label: 'Mozambique (MZ)' },
  { code: 'MM', label: 'Myanmar (MM)' },
  { code: 'NA', label: 'Namibia (NA)' },
  { code: 'NR', label: 'Nauru (NR)' },
  { code: 'NP', label: 'Nepal (NP)' },
  { code: 'NL', label: 'Netherlands (NL)' },
  { code: 'NC', label: 'New Caledonia (NC)' },
  { code: 'NZ', label: 'New Zealand (NZ)' },
  { code: 'NI', label: 'Nicaragua (NI)' },
  { code: 'NE', label: 'Niger (NE)' },
  { code: 'NG', label: 'Nigeria (NG)' },
  { code: 'NU', label: 'Niue (NU)' },
  { code: 'NF', label: 'Norfolk Island (NF)' },
  { code: 'MK', label: 'North Macedonia (MK)' },
  { code: 'MP', label: 'Northern Mariana Islands (MP)' },
  { code: 'NO', label: 'Norway (NO)' },
  { code: 'OM', label: 'Oman (OM)' },
  { code: 'PK', label: 'Pakistan (PK)' },
  { code: 'PW', label: 'Palau (PW)' },
  { code: 'PS', label: 'Palestine, State of (PS)' },
  { code: 'PA', label: 'Panama (PA)' },
  { code: 'PG', label: 'Papua New Guinea (PG)' },
  { code: 'PY', label: 'Paraguay (PY)' },
  { code: 'PE', label: 'Peru (PE)' },
  { code: 'PH', label: 'Philippines (PH)' },
  { code: 'PN', label: 'Pitcairn (PN)' },
  { code: 'PL', label: 'Poland (PL)' },
  { code: 'PT', label: 'Portugal (PT)' },
  { code: 'PR', label: 'Puerto Rico (PR)' },
  { code: 'QA', label: 'Qatar (QA)' },
  { code: 'RE', label: 'Réunion (RE)' },
  { code: 'RO', label: 'Romania (RO)' },
  { code: 'RU', label: 'Russian Federation (RU)' },
  { code: 'RW', label: 'Rwanda (RW)' },
  { code: 'BL', label: 'Saint Barthélemy (BL)' },
  { code: 'SH', label: 'Saint Helena, Ascension and Tristan da Cunha (SH)' },
  { code: 'KN', label: 'Saint Kitts and Nevis (KN)' },
  { code: 'LC', label: 'Saint Lucia (LC)' },
  { code: 'MF', label: 'Saint Martin (French part) (MF)' },
  { code: 'PM', label: 'Saint Pierre and Miquelon (PM)' },
  { code: 'VC', label: 'Saint Vincent and the Grenadines (VC)' },
  { code: 'WS', label: 'Samoa (WS)' },
  { code: 'SM', label: 'San Marino (SM)' },
  { code: 'ST', label: 'Sao Tome and Principe (ST)' },
  { code: 'SA', label: 'Saudi Arabia (SA)' },
  { code: 'SN', label: 'Senegal (SN)' },
  { code: 'RS', label: 'Serbia (RS)' },
  { code: 'SC', label: 'Seychelles (SC)' },
  { code: 'SL', label: 'Sierra Leone (SL)' },
  { code: 'SG', label: 'Singapore (SG)' },
  { code: 'SX', label: 'Sint Maarten (Dutch part) (SX)' },
  { code: 'SK', label: 'Slovakia (SK)' },
  { code: 'SI', label: 'Slovenia (SI)' },
  { code: 'SB', label: 'Solomon Islands (SB)' },
  { code: 'SO', label: 'Somalia (SO)' },
  { code: 'ZA', label: 'South Africa (ZA)' },
  { code: 'GS', label: 'South Georgia and the South Sandwich Islands (GS)' },
  { code: 'SS', label: 'South Sudan (SS)' },
  { code: 'ES', label: 'Spain (ES)' },
  { code: 'LK', label: 'Sri Lanka (LK)' },
  { code: 'SD', label: 'Sudan (SD)' },
  { code: 'SR', label: 'Suriname (SR)' },
  { code: 'SJ', label: 'Svalbard and Jan Mayen (SJ)' },
  { code: 'SE', label: 'Sweden (SE)' },
  { code: 'CH', label: 'Switzerland (CH)' },
  { code: 'SY', label: 'Syrian Arab Republic (SY)' },
  { code: 'TJ', label: 'Tajikistan (TJ)' },
  { code: 'TZ', label: 'Tanzania, United Republic of (TZ)' },
  { code: 'TH', label: 'Thailand (TH)' },
  { code: 'TL', label: 'Timor-Leste (TL)' },
  { code: 'TG', label: 'Togo (TG)' },
  { code: 'TK', label: 'Tokelau (TK)' },
  { code: 'TO', label: 'Tonga (TO)' },
  { code: 'TT', label: 'Trinidad and Tobago (TT)' },
  { code: 'TN', label: 'Tunisia (TN)' },
  { code: 'TR', label: 'Turkey (TR)' },
  { code: 'TM', label: 'Turkmenistan (TM)' },
  { code: 'TC', label: 'Turks and Caicos Islands (TC)' },
  { code: 'TV', label: 'Tuvalu (TV)' },
  { code: 'UG', label: 'Uganda (UG)' },
  { code: 'UA', label: 'Ukraine (UA)' },
  { code: 'AE', label: 'United Arab Emirates (AE)' },
  { code: 'GB', label: 'United Kingdom (GB)' },
  { code: 'US', label: 'United States (US)' },
  { code: 'UM', label: 'United States Minor Outlying Islands (UM)' },
  { code: 'UY', label: 'Uruguay (UY)' },
  { code: 'UZ', label: 'Uzbekistan (UZ)' },
  { code: 'VU', label: 'Vanuatu (VU)' },
  { code: 'VE', label: 'Venezuela (VE)' },
  { code: 'VN', label: 'Viet Nam (VN)' },
  { code: 'VG', label: 'Virgin Islands (British) (VG)' },
  { code: 'VI', label: 'Virgin Islands (U.S.) (VI)' },
  { code: 'WF', label: 'Wallis and Futuna (WF)' },
  { code: 'EH', label: 'Western Sahara (EH)' },
  { code: 'YE', label: 'Yemen (YE)' },
  { code: 'ZM', label: 'Zambia (ZM)' },
  { code: 'ZW', label: 'Zimbabwe (ZW)' },
]

// Actions
function selectDomestic() {
  region.value = 'domestic'
  step.value = 2
}

function selectOverseas() {
  region.value = 'overseas'
  step.value = 2
}

async function confirmDomestic() {
  const code = selectedProvince.value
  if (!code) return

  const provinceName = provinceNameMap[code]
  const country = provinceCountryMap[code]

  let countryCode: string
  let countryName: string
  let regionValue: string

  if (country) {
    // HK, MO, TW
    countryCode = country.code
    countryName = country.name
    regionValue = provinceName
  } else {
    // Mainland China provinces
    countryCode = 'CN'
    countryName = '中国'
    regionValue = provinceName
  }

  try {
    await updateUserGeo({
      user_id: props.userId,
      region: regionValue,
      country_code: countryCode,
      country_name: countryName,
    })
    chatStore.setUserGeo(regionValue, countryCode, countryName, true)
    emit('confirmed')
  } catch {
    alert('保存失败，请重试')
  }
}

async function confirmOverseas() {
  const code = selectedCountry.value
  if (!code) return

  const countryOption = overseasOptions.find((c) => c.code === code)
  const countryName = countryOption
    ? countryOption.label.replace(/\s*\([A-Z]{2}\)\s*$/, '')
    : code

  try {
    await updateUserGeo({
      user_id: props.userId,
      region: '海外',
      country_code: code,
      country_name: countryName,
    })
    chatStore.setUserGeo('海外', code, countryName, true)
    emit('confirmed')
  } catch {
    alert('保存失败，请重试')
  }
}
</script>

<style scoped>
/* ========================================
   弹窗核心样式（从 ChatView.vue 同步）
   ======================================== */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.5);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: geo-fade-in 0.2s var(--ease-out);
}

@keyframes geo-fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

.modal-box {
  background: #fff;
  border-radius: var(--radius-xl);
  padding: 32px 28px 24px;
  width: 400px;
  max-width: 92vw;
  box-shadow: var(--shadow-xl), 0 0 0 1px rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
  gap: 14px;
  animation: geo-modal-in 0.3s var(--ease-out-back);
}

@keyframes geo-modal-in {
  from {
    opacity: 0;
    transform: translateY(24px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.modal-title {
  font-size: 19px;
  font-weight: 700;
  color: var(--color-text-primary);
}

.modal-desc {
  font-size: 13.5px;
  color: var(--color-text-secondary);
  margin: 0;
  line-height: 1.6;
}

.modal-input {
  width: 100%;
  padding: 11px 14px;
  border: 2px solid var(--color-border);
  border-radius: var(--radius-md);
  background: #fff;
  color: var(--color-text-primary);
  font-size: 14px;
  font-family: var(--font-sans);
  outline: none;
  transition: all var(--duration-fast) var(--ease-out);
}

.modal-input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.08);
}

.modal-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 6px;
}

.modal-confirm-btn {
  padding: 10px 22px;
  background: var(--color-primary-gradient);
  color: #fff;
  border: none;
  border-radius: var(--radius-md);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.3);
}

.modal-confirm-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(99, 102, 241, 0.45);
}

.modal-confirm-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  box-shadow: none;
}

.modal-cancel-btn {
  padding: 10px 18px;
  background: transparent;
  color: var(--color-text-secondary);
  border: 1.5px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 14px;
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.modal-cancel-btn:hover {
  background: var(--color-bg);
  border-color: var(--color-text-muted);
}

/* ========================================
   组件专属样式
   ======================================== */
.geo-modal-box {
  width: 460px;
  max-width: 94vw;
}

.geo-options {
  display: flex;
  gap: 12px;
  margin: 4px 0;
}

.geo-option-btn {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 20px 16px;
  border: 2px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: #fff;
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.geo-option-btn:hover {
  border-color: var(--color-primary);
  background: var(--color-primary-light);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.15);
}

.geo-option-icon {
  font-size: 32px;
}

.geo-option-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.geo-select {
  width: 100%;
  padding: 8px;
  border: 2px solid var(--color-border);
  border-radius: var(--radius-md);
  background: #fff;
  color: var(--color-text-primary);
  font-size: 14px;
  font-family: var(--font-sans);
  outline: none;
  overflow-y: auto;
}

.geo-select:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.08);
}

.geo-select option {
  padding: 6px 8px;
}

/* ========================================
   深色模式
   ======================================== */
:global(.chat-container.dark-theme) .modal-box {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
}

:global(.chat-container.dark-theme) .modal-input {
  background: var(--color-bg);
}

:global(.chat-container.dark-theme) .modal-input:focus {
  background: var(--color-surface);
}

:global(.chat-container.dark-theme) .modal-cancel-btn:hover {
  background: var(--color-bg);
}

:global(.chat-container.dark-theme) .geo-option-btn {
  background: var(--color-surface);
  border-color: var(--color-border);
}

:global(.chat-container.dark-theme) .geo-option-btn:hover {
  border-color: var(--color-primary);
  background: rgba(99, 102, 241, 0.1);
}

:global(.chat-container.dark-theme) .geo-select {
  background: var(--color-bg);
  border-color: var(--color-border);
  color: var(--color-text-primary);
}
</style>
