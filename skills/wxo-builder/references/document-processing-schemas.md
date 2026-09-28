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

| Category | Document Type (`schema_name`) | Table / Array Fields | Typical Key Fields |
|---|---|---|---|
| **Accounting & Financial** | `Invoice` | `line_items` (amount, description, product_code, quantity, unit, unit_price) | `invoice_id`, `invoice_date`, `due_date`, `vendor_name`, `customer_name`, `sub_total`, `tax`, `total`, `currency` |
| | `PurchaseOrder` | `items` (description, item_number, quantity, unit_price, total_price) | `po_number`, `order_date`, `buyer_name`, `vendor_name`, `total_amount`, `payment_terms` |
| | `Receipt` | None / optional line items | `receipt_id`, `merchant_name`, `transaction_date`, `total_amount`, `tax_amount`, `payment_method` |
| | `ExpenseReport` | `expenses` | `report_id`, `employee_name`, `employee_id`, `report_period_start`, `report_period_end`, `subtotal`, `total_reimbursement_amount` |
| **Banking & Statements** | `BankStatement` | `transactions` (date, description, amount, balance) | `bank_name`, `account_number`, `statement_period_start`, `statement_period_end`, `opening_balance`, `closing_balance` |
| | `CreditCardStatement` | `transactions` (date, description, amount) | `card_issuer`, `card_last_four`, `statement_date`, `payment_due_date`, `minimum_payment`, `new_balance` |
| | `RemittanceAdvice` | `invoices_paid` | `remittance_id`, `payment_date`, `payer_name`, `payee_name`, `total_payment_amount`, `check_number` |
| **Taxation & Compliance** | `TaxForm_W9_1099_941_1120` | None | `taxpayer_name`, `business_name`, `tin_or_ssn`, `tax_year`, `federal_tax_classification`, `exempt_payee_code` |
| | `FinancialStatement` | `line_items` | `company_name`, `statement_type`, `period_ended`, `revenue`, `net_income`, `total_assets`, `total_liabilities` |
| **Logistics & Shipping** | `BillOfLading` | None / items | `bill_of_lading_number`, `shipper_name`, `shipper_address`, `consignee_name`, `carrier_name`, `origin`, `destination`, `gross_weight` |
| | `CustomsForm` | `declared_items` | `customs_form_number`, `shipper_exporter_name`, `destination_country`, `total_value`, `hs_tariff_code` |
| | `DeliveryReceipt` | None / items | `delivery_receipt_number`, `carrier_name`, `date_of_delivery`, `recipient_name`, `recipient_signature` |
| **Real Estate & Lending** | `MortgageLending` | None | `loan_reference_number`, `borrower_name`, `lender_name`, `property_address`, `loan_principal_amount`, `interest_rate`, `monthly_payment` |
| **Human Resources** | `I9Form` | None | `employee_first_name`, `employee_last_name`, `date_of_birth`, `ssn`, `citizenship_status`, `document_title`, `expiration_date` |
| | `W4Form` | None | `first_name`, `last_name`, `ssn`, `marital_status`, `multiple_jobs_or_spouse`, `claim_dependents_amount`, `extra_withholding` |
| **Identity & KYC** | `DriversLicense` | None | `license_number`, `first_name`, `last_name`, `date_of_birth`, `address`, `issue_date`, `expiration_date`, `state` |
| | `NationalIdCard` | None | `id_number`, `full_name`, `date_of_birth`, `gender`, `nationality`, `issue_date`, `expiry_date` |
| | `TravelPassport` | None | `passport_number`, `surname`, `given_names`, `nationality`, `date_of_birth`, `date_of_issue`, `date_of_expiry` |
| | `UtilityBill` | None | `utility_provider`, `customer_name`, `service_address`, `billing_date`, `due_date`, `amount_due`, `account_number` |
| **Insurance** | `AcordForm` | None | `policy_number`, `insured_name`, `producer_name`, `effective_date`, `expiration_date`, `coverage_types`, `limits` |
| | `LifeDisabilityClaimForm` | None | `claimant_name`, `policy_number`, `date_of_disability`, `attending_physician`, `diagnosis`, `employer_name` |
| | `DeathClaimForm` | None | `deceased_name`, `date_of_death`, `policy_number`, `beneficiary_name`, `cause_of_death` |
| | `DisabilityStandardForm` | None | `patient_name`, `claim_number`, `disability_type`, `onset_date`, `physician_signature` |
| **Healthcare** | `InsuranceClaim` | `service_lines` (date, procedure_code, charge) | `patient_name`, `insured_id`, `provider_name`, `total_charge`, `diagnosis_codes`, `facility_type` |
| | `PatientIntakeForm` | None | `patient_name`, `dob`, `gender`, `emergency_contact`, `allergies`, `primary_insurance_carrier`, `policy_id` |
| **Education** | `DiplomaCertification` | None | `recipient_name`, `institution_name`, `degree_title`, `major_field`, `graduation_date`, `honors` |
| | `AcademicTranscript` | `coursework` (course_code, title, credits, grade) | `student_name`, `student_id`, `institution`, `cumulative_gpa`, `degree_awarded`, `dates_of_attendance` |
| **Regulatory** | `BusinessLicensePermit` | None | `license_number`, `business_name`, `issuing_authority`, `license_type`, `effective_date`, `expiration_date` |

---

## 3. Dual Schema Implementation Patterns

### Pattern A: Structured Document Extractor with Tables (`aflow.docext`)

When extracting custom or predefined schemas using `docext`, convert fields into Pydantic models with `DocExtConfigField` and `DocExtConfigTableField`:

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
        description="Extracts invoice header and itemized line items table",
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
        kvp_force_schema_name="UtilityBill",     # Name of the predefined schema
    )
    aflow.sequence(START, doc_node, END)
    return aflow
```

---

## 4. Multi-Document Classification & Routing Blueprint

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
