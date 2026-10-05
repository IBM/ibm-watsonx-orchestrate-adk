# Document Processing & Extraction Schemas Reference

This reference covers the watsonx Orchestrate document processing nodes: `aflow.docext` (Structured / Unstructured Extractor), `aflow.docclassifier` (Document Classifier), and `aflow.docproc` (Text Extraction / KVP OCR).

---

## 1. Node Selection & Triage

When building a flow that processes documents, evaluate the customer's document format and goals:

| Goal | Recommended Node | `field_extraction_method` | Table Support | Input Schema | Output Type |
|---|---|---|---|---|---|
| **Extract typed fields + tables** from fixed-layout documents (Invoices, POs, Receipts, Tax forms, Forms — typically 1–3 pages) | `aflow.docext()` | `"layout"` (Structured — vision model) | ✅ **Yes** (`DocExtConfigTableField`) | `DocumentProcessingCommonInput` | Tuple `(node, OutputSchema)` with typed attribute access |
| **Extract typed top-level fields** from text-heavy, multi-page documents (Contracts, Emails, Manuals, Legal briefs) | `aflow.docext()` | `"classic"` (Unstructured — text model) | ❌ **No** — does not extract column values from tables | `DocumentProcessingCommonInput` | Tuple `(node, OutputSchema)` with typed attribute access |
| **Extract document content** — raw text, Markdown, or HTML — for downstream summarization or analysis; also produces KVPs | `aflow.docproc()` | `task="text_extraction"` | ✅ KVP arrays included in output | `DocProcInput` | `DocProcOutputFormat.object` (`text`, `kvps`) |
| **Classify & route multiple document types** | `aflow.docclassifier()` | N/A | N/A | `DocumentProcessingCommonInput` | `DocumentClassificationResponse` (`class_name`) |

### Design Rules:
1. **Table and options require Structured extraction:** `DocExtConfigTableField` and `available_options` (enums) are only supported with `field_extraction_method="layout"`. If your use case includes tables or constrained options, choose the Structured extractor.
2. **Page ranges require Structured extraction:** `PageRange(start=X, end=Y)` is only available with `field_extraction_method="layout"`.
3. **Prefer `docext` for field/table extraction:** When the goal is extracting specific typed fields or tables, use `docext` (`"layout"` or `"classic"`). Use `docproc` when you need the document's textual content (raw text, Markdown, HTML) or are feeding output into a summarization/analysis prompt.
4. **File Upload Handling:** Flows using `DocumentProcessingCommonInput` or `DocProcInput` handle the interactive file upload prompt automatically. The agent YAML instructions must **never** prompt the user to upload a file before calling the flow.

---

## 2. Predefined 28 B2B Document Schemas Catalog

The document processing engine ships with 28 pre-built schemas organized into 11 business domains.

### Catalog Summary Index:

⚠️ **`kvp_force_schema_name` must be the exact string from the table below** — the engine validates this value case-insensitively but rejects any variation not in its list. Do not invent CamelCase or shorthand names. The `docext` label column is for reference only (used when translating to `DocExtConfigField` declarations).

| Category | Display Name | `kvp_force_schema_name` (exact, for `docproc`) | Table / Array Fields | Typical Key Fields |
|---|---|---|---|---|
| **Accounting & Financial** | Invoice | `invoice` | `line_items` (amount, description, product_code, quantity, unit, unit_price) | `invoice_id`, `invoice_date`, `due_date`, `vendor_name`, `customer_name`, `sub_total`, `tax`, `total`, `currency` |
| | Purchase Order | `purchase_order` | `items` (description, item_number, quantity, unit_price, total_price) | `po_number`, `order_date`, `buyer_name`, `vendor_name`, `total_amount`, `payment_terms` |
| | Receipt | `receipt` | None / optional line items | `receipt_id`, `merchant_name`, `transaction_date`, `total_amount`, `tax_amount`, `payment_method` |
| | Expense Reports | `expense_reports` | `expenses` | `report_id`, `employee_name`, `employee_id`, `report_period_start`, `report_period_end`, `subtotal`, `total_reimbursement_amount` |
| **Banking & Statements** | Bank Statements | `bank_statements` | `transactions` (date, description, amount, balance) | `bank_name`, `account_number`, `statement_period_start`, `statement_period_end`, `opening_balance`, `closing_balance` |
| | Credit Card Statements | `credit_card_statements` | `transactions` (date, description, amount) | `card_issuer`, `card_last_four`, `statement_date`, `payment_due_date`, `minimum_payment`, `new_balance` |
| | Remittance / Payment Advice | `remittance_/_payment_advice` | `invoices_paid` | `remittance_id`, `payment_date`, `payer_name`, `payee_name`, `total_payment_amount`, `check_number` |
| **Taxation & Compliance** | Tax Forms (W-9, 1099, 941, 1120) | `tax_forms_(w-9,_1099,_941,_1120)` | None | `taxpayer_name`, `business_name`, `tin_or_ssn`, `tax_year`, `federal_tax_classification`, `exempt_payee_code` |
| | Financial Statement | `financial_statement` | `line_items` | `company_name`, `statement_type`, `period_ended`, `revenue`, `net_income`, `total_assets`, `total_liabilities` |
| **Logistics & Shipping** | Bill of Lading | `bill_of_lading` | None / items | `bill_of_lading_number`, `shipper_name`, `shipper_address`, `consignee_name`, `carrier_name`, `origin`, `destination`, `gross_weight` |
| | Customs Form | `customs_form` | `declared_items` | `customs_form_number`, `shipper_exporter_name`, `destination_country`, `total_value`, `hs_tariff_code` |
| | Delivery Receipt | `delivery_receipt` | None / items | `delivery_receipt_number`, `carrier_name`, `date_of_delivery`, `recipient_name`, `recipient_signature` |
| **Real Estate & Lending** | Mortgage / Lending Document | `mortgage_/_lending_document` | None | `loan_reference_number`, `borrower_name`, `lender_name`, `property_address`, `loan_principal_amount`, `interest_rate`, `monthly_payment` |
| **Human Resources** | I-9 Form | `i-9_form` | None | `employee_first_name`, `employee_last_name`, `date_of_birth`, `ssn`, `citizenship_status`, `document_title`, `expiration_date` |
| | W-4 Form | `w-4_form` | None | `first_name`, `last_name`, `ssn`, `marital_status`, `multiple_jobs_or_spouse`, `claim_dependents_amount`, `extra_withholding` |
| **Identity & KYC** | Driver's License | `driver_license` | None | `license_number`, `first_name`, `last_name`, `date_of_birth`, `address`, `issue_date`, `expiration_date`, `state` |
| | National ID Card | `national_id_card` | None | `id_number`, `full_name`, `date_of_birth`, `gender`, `nationality`, `issue_date`, `expiry_date` |
| | Travel Passport | `passport` | None | `passport_number`, `surname`, `given_names`, `nationality`, `date_of_birth`, `date_of_issue`, `date_of_expiry` |
| | Utility Bill | `utility_bill` | None | `utility_provider`, `customer_name`, `service_address`, `billing_date`, `due_date`, `amount_due`, `account_number` |
| **Insurance** | ACORD Insurance Form | `acord_insurance_form` | None | `policy_number`, `insured_name`, `producer_name`, `effective_date`, `expiration_date`, `coverage_types`, `limits` |
| | Life/Disability Claim (Claimant's Statement) | `claimant's_statement` | None | `claimant_name`, `policy_number`, `date_of_disability`, `attending_physician`, `diagnosis`, `employer_name` |
| | Initial Claimant's Statement (Income Replacement) | `initial_claimant's_statement_for_income_replacement/waiver_of_premium_benefits` | None | `patient_name`, `claim_number`, `disability_type`, `onset_date`, `physician_signature` |
| | Life Insurance Authorization Form | `life_insurance_authorization_form` | None | `deceased_name`, `date_of_death`, `policy_number`, `beneficiary_name`, `cause_of_death` |
| **Healthcare** | Insurance Claim | `insurance_claim` | `service_lines` (date, procedure_code, charge) | `patient_name`, `insured_id`, `provider_name`, `total_charge`, `diagnosis_codes`, `facility_type` |
| | Patient Intake Form | `patient_intake_form` | None | `patient_name`, `dob`, `gender`, `emergency_contact`, `allergies`, `primary_insurance_carrier`, `policy_id` |
| **Education** | Diploma / Certification | `diploma_/_certification` | None | `recipient_name`, `institution_name`, `degree_title`, `major_field`, `graduation_date`, `honors` |
| | Academic Transcripts | `transcripts` | `coursework` (course_code, title, credits, grade) | `student_name`, `student_id`, `institution`, `cumulative_gpa`, `degree_awarded`, `dates_of_attendance` |
| **Regulatory** | Business Licenses & Permits | `business_licenses_&_permits` | None | `license_number`, `business_name`, `issuing_authority`, `license_type`, `effective_date`, `expiration_date` |

### Using the catalog as a field-definition source for `docext`

The catalog above serves two independent purposes:

1. **`aflow.docproc` trigger** — pass `kvp_schemas=[]` + `kvp_force_schema_name="<schema_name>"` to activate the server-side schema by name (no field declarations needed).
2. **`aflow.docext` field blueprint** — translate any catalog row into `DocExtConfigField` / `DocExtConfigTableField` declarations to use with the Structured or Unstructured extractor. The `field_name` values in the catalog become the `field_name` keys in the Pydantic model; table columns become nested `DocExtConfigField` entries inside a `DocExtConfigTableField`.

**Translation is always valid and produces structurally identical output.** When a customer asks to "use the predefined schema" for a `docext` node, translate the catalog row into the Pydantic model — do not say it is impossible. The two representations are equivalent; the catalog entry is simply the canonical source of truth for field names and types.

**When to translate vs. when to ask:** If the customer names a document type that matches a catalog entry (e.g. "Invoice", "Utility Bill", "Bank Statement"), translate the full catalog row automatically and present it. Ask the customer only if they want to add, remove, or rename fields relative to the catalog baseline.

---

## 3. Dual Schema Implementation Patterns

### Pattern A: Structured Document Extractor with Tables (`aflow.docext`)

When extracting custom or predefined schemas using `docext`, convert fields into Pydantic models with `DocExtConfigField` and `DocExtConfigTableField`. The predefined catalog in §2 is a valid source for these field definitions — translate it directly when the customer requests a known document type:

```python
from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.flow_builder.flows import Flow, flow, START, END
from ibm_watsonx_orchestrate.flow_builder.types import (
    DocExtConfigField, DocExtConfigTableField, DocumentProcessingCommonInput, PageRange
)

class InvoiceExtractorFields(BaseModel):
    invoice_number: DocExtConfigField = Field(
        default=DocExtConfigField(name="Invoice Number", field_name="invoice_id")
    )
    invoice_date: DocExtConfigField = Field(
        default=DocExtConfigField(name="Invoice Date", field_name="invoice_date", type="date")
    )
    total_amount: DocExtConfigField = Field(
        default=DocExtConfigField(name="Total Amount", field_name="total", type="number")
    )
    currency: DocExtConfigField = Field(
        default=DocExtConfigField(
            name="Currency", field_name="currency",
            available_options=["USD", "EUR", "GBP", "CAD", "AUD"]
        )
    )
    # Repeating Table:
    line_items: DocExtConfigTableField = Field(
        default=DocExtConfigTableField(
            name="Line Items",
            field_name="line_items",
            description="Itemized list of billed goods or services.",
            fields=[
                DocExtConfigField(name="Description", field_name="description", type="string"),
                DocExtConfigField(name="Quantity", field_name="quantity", type="number"),
                DocExtConfigField(name="Unit Price", field_name="unit_price", type="number"),
                DocExtConfigField(name="Amount", field_name="amount", type="number"),
            ]
        )
    )

@flow(name="extract_invoice_flow", input_schema=DocumentProcessingCommonInput)
def build_extract_invoice_flow(aflow: Flow) -> Flow:
    extractor_node, _Schema = aflow.docext(
        name="invoice_extractor",
        display_name="Invoice Extractor",
        description="Extracts invoice fields and line items table",
        llm="watsonx/mistralai/mistral-small-3-1-24b-instruct-2503",
        fields=InvoiceExtractorFields(),
        field_extraction_method="layout",   # Required for tables and available_options
        # enable_hw=True,                   # Add only if documents may contain handwritten text
    )
    aflow.sequence(START, extractor_node, END)
    return aflow
```

---

### Pattern B: Predefined Schema Trigger (`aflow.docproc`)

When using `docproc` for text extraction and KVP, reference built-in predefined schemas by setting `kvp_schemas=[]` (empty list) and naming the schema in `kvp_force_schema_name`:

```python
from ibm_watsonx_orchestrate.flow_builder.flows import Flow, flow, START, END
from ibm_watsonx_orchestrate.flow_builder.types import DocProcInput, DocProcOutputFormat

@flow(name="extract_utility_bill_flow", input_schema=DocProcInput)
def build_utility_bill_flow(aflow: Flow) -> Flow:
    doc_node = aflow.docproc(
        name="utility_extractor",
        display_name="Utility Bill Extractor",
        description="Extracts KVPs using the predefined UtilityBill schema",
        task="text_extraction",
        output_format=DocProcOutputFormat.object,
        kvp_schemas=[],                          # Empty list activates server-side predefined schema catalog
        kvp_force_schema_name="utility_bill",    # Exact name from the catalog table — see §2
    )
    aflow.sequence(START, doc_node, END)
    return aflow
```

---

## 4. Output Format Comparison: `docproc` vs `docext`

The two extraction nodes produce **structurally different output**, which directly affects how downstream nodes consume results. This is a key factor in node selection when the goal is field or table extraction.

### `docext` output — typed object with named properties

`aflow.docext()` returns a `(node, OutputSchema)` tuple. The extracted fields are accessible as typed attributes on the node output:

```python
# Direct attribute access in downstream nodes / script expressions:
flow.invoice_extractor.output.invoice_id      # str
flow.invoice_extractor.output.invoice_date    # str (ISO-8601)
flow.invoice_extractor.output.total           # float
flow.invoice_extractor.output.line_items      # list of row objects

# Each table row is a typed object:
flow.invoice_extractor.output.line_items[0].description   # str
flow.invoice_extractor.output.line_items[0].unit_price    # float
```

**Output shape (JSON equivalent):**
```json
{
  "invoice_id": "INV-2024-00142",
  "invoice_date": "2024-11-15",
  "total": 4750.00,
  "line_items": [
    { "description": "Consulting Services", "quantity": 10, "unit_price": 350.00, "amount": 3500.00 },
    { "description": "Travel Expenses",     "quantity": 1,  "unit_price": 750.00, "amount": 750.00  }
  ]
}
```

---

### `docproc` output — flat `kvps[]` array

`aflow.docproc()` with `output_format=DocProcOutputFormat.object` returns a flat list of KVP objects. Each single-value field is one element; **table rows are also flattened into this same array**, distinguished by `group_id` or `table_id` metadata — they are NOT returned as a nested list.

```json
{
  "kvps": [
    { "key": { "semantic_label": "invoice_id" },   "value": { "raw_text": "INV-2024-00142" } },
    { "key": { "semantic_label": "total" },         "value": { "raw_text": "4750.00" } },
    { "key": { "semantic_label": "description" },   "value": { "raw_text": "Consulting Services" }, "group_id": "row_0" },
    { "key": { "semantic_label": "unit_price" },    "value": { "raw_text": "350.00" },              "group_id": "row_0" },
    { "key": { "semantic_label": "description" },   "value": { "raw_text": "Travel Expenses" },     "group_id": "row_1" },
    { "key": { "semantic_label": "unit_price" },    "value": { "raw_text": "750.00" },              "group_id": "row_1" }
  ]
}
```

To recover table rows you must **group by `group_id`** — there is no built-in structured table object. Scalar fields require key lookup by `semantic_label`. All values are raw strings regardless of the declared field type.

---

### Side-by-side comparison

| | `docext` | `docproc` |
|---|---|---|
| **Output shape** | Typed object — fields as named properties | Flat `kvps[]` array of `{key, value}` objects |
| **Field access** | `output.invoice_id`, `output.total` | `[k for k in kvps if k["key"]["semantic_label"]=="invoice_id"][0]["value"]["raw_text"]` |
| **Table rows** | `output.line_items` — list of typed row objects | Flattened into `kvps[]`, grouped by `group_id` — requires manual groupby to reconstruct rows |
| **Value types** | Typed: `number` → `float`, `date` → ISO string | Always raw string — caller must parse/cast |
| **Downstream use** | Direct attribute access in `aflow.script`, `aflow.prompt`, `aflow.conditions` | Pass full `kvps` array to a prompt node (let LLM parse), or write list comprehensions |
| **Recommended when** | Structured field/table extraction for downstream processing | Document content (text/Markdown/HTML) needed, or feeding raw output to an LLM summarizer |

**Rule of thumb:** if any downstream node needs to read individual field values or iterate table rows programmatically, use `docext`. Reserve `docproc` for document content extraction or cases where the full output is passed verbatim to a prompt node.

---

## 5. Multi-Document Classification & Routing Blueprint

When multiple document formats must be handled dynamically, classify first with `aflow.docclassifier()`, then branch with `aflow.conditions()` to dedicated extractors, and merge into a consolidation node:

```python
from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.flow_builder.flows import Flow, flow, START, END, Branch
from ibm_watsonx_orchestrate.flow_builder.types import (
    DocClassifierClass, DocExtConfigField, DocumentProcessingCommonInput
)

class DocTypes(BaseModel):
    invoice: DocClassifierClass = Field(default=DocClassifierClass(class_name="Invoice"))
    utility_bill: DocClassifierClass = Field(default=DocClassifierClass(class_name="UtilityBill"))

class ConsolidatedResult(BaseModel):
    document_type: str
    extracted_summary: str

@flow(name="classify_and_extract_flow", input_schema=DocumentProcessingCommonInput, output_schema=ConsolidatedResult)
def build_classify_and_extract_flow(aflow: Flow) -> Flow:
    # 1. Classifier Node
    classifier = aflow.docclassifier(
        name="doc_classifier",
        display_name="Classify Document",
        description="Identifies document category",
        llm="watsonx/meta-llama/llama-4-maverick-17b-128e-instruct-fp8",
        classes=DocTypes(),
    )

    # 2. Specialized Extractor Nodes
    invoice_ext, _ = aflow.docext(
        name="invoice_extractor",
        display_name="Extract Invoice",
        description="Extracts invoice fields",
        fields=InvoiceExtractorFields(),
        field_extraction_method="layout",
    )

    utility_ext, _ = aflow.docext(
        name="utility_extractor",
        display_name="Extract Utility",
        description="Extracts utility bill fields",
        fields=UtilityBillFields(),
        field_extraction_method="layout",
    )

    # 3. Consolidation Node (prevents empty output dictionary)
    consolidate = aflow.script(
        name="consolidate_output",
        script="""
self.output.document_type = flow.doc_classifier.output.class_name
if flow.doc_classifier.output.class_name.lower() == 'invoice':
    self.output.extracted_summary = f"Invoice #{flow.invoice_extractor.output.invoice_id} Total: {flow.invoice_extractor.output.total}"
else:
    self.output.extracted_summary = f"Utility Bill #{flow.utility_extractor.output.account_number} Due: {flow.utility_extractor.output.amount_due}"
""",
        output_schema=ConsolidatedResult,
    )

    # 4. Router Branch
    router: Branch = aflow.conditions(name="route_by_type")
    router.condition(
        expression="flow.doc_classifier.output.class_name.strip().lower() == 'invoice'",
        to_node=invoice_ext
    ).condition(
        expression="flow.doc_classifier.output.class_name.strip().lower() == 'utilitybill'",
        to_node=utility_ext
    ).condition(
        default=True,
        to_node=invoice_ext
    )

    # 5. Wiring
    aflow.sequence(START, classifier, router)
    aflow.edge(invoice_ext, consolidate)
    aflow.edge(utility_ext, consolidate)
    aflow.edge(consolidate, END)

    return aflow
```
