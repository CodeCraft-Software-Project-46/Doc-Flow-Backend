import hashlib
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from unittest.mock import patch

from .models import DocumentType, Document, ExternalWorkflowInstance, ManualUploadDocument

class ManualUploadCriticalPathTests(TestCase):
    
    def setUp(self):
        """
        This runs BEFORE every single test. 
        It sets up our dummy database data and API client.
        """
        self.client = APIClient()
        
        # Create a dummy Document Type in our test database
        self.doc_type = DocumentType.objects.create(
            type_name="Test Invoice",
            category="Finance",
            allowed_extensions="pdf,jpg,png",
            is_active=True
        )
        
        # The URL to manual upload endpoint
        self.upload_url = '/api/documents/upload/manual/'

    # ---------------------------------------------------------
    # TEST 1: The "Wrong File Type" Rejection Test
    # ---------------------------------------------------------
    def test_upload_wrong_file_type_rejected(self):
        # This test case ensures that if someone tries to upload a file with an extension that is not allowed,
        # the system correctly rejects it and does not save anything to the database.
        
        # Simulate a malicious executable file
        bad_file = SimpleUploadedFile(
            "abc.exe", 
            b"fake malicious content", 
            content_type="application/x-msdownload"
        )
        
        response = self.client.post(self.upload_url, {
            'file': bad_file,
            'document_type_id': self.doc_type.id,
            'workflow_id': 'test-workflow-123'
        }, format='multipart')

        # We expect a 400 Bad Request
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid file type", response.data['error'])
        
        # Verify nothing was saved to the database
        self.assertEqual(Document.objects.count(), 0)

    # ---------------------------------------------------------
    # TEST 2: The "Duplicate File" Prevention Test
    # ---------------------------------------------------------
    def test_duplicate_file_hash_rejected(self):
        # This test case ensures that if someone tries to upload an existing document,
        
        file_content = b"This is my test document content."
        
        # 1. Manually calculate the hash and inject a fake document into the DB
        file_hash = hashlib.sha256(file_content).hexdigest()
        Document.objects.create(
            document_name="original.pdf",
            document_type=self.doc_type,
            source='manual',
            file_hash=file_hash,
            ai_summary="Mock summary",
            s3_url="https://mock.s3.com/original.pdf"
        )
        
        # 2. Try to upload a new file with the EXACT SAME content
        duplicate_file = SimpleUploadedFile(
            "duplicate.pdf", 
            file_content, 
            content_type="application/pdf"
        )
        
        response = self.client.post(self.upload_url, {
            'file': duplicate_file,
            'document_type_id': self.doc_type.id,
            'workflow_id': 'test-workflow-123'
        }, format='multipart')

        # We expect a 409 Conflict (Duplicate)
        self.assertEqual(response.status_code, 409)
        self.assertIn("already been uploaded", response.data['error'])
        
        # Verify the DB still only has 1 document, not 2
        self.assertEqual(Document.objects.count(), 1)

    # ---------------------------------------------------------
    # TEST 3: The Perfect Manual Upload Test (With Mocks)
    # ---------------------------------------------------------
    # We use @patch to hijack S3 and AI services so they don't actually run.
    @patch('documents.views.ExternalWorkflowInstance.objects.create')
    @patch('documents.views.S3Service')
    @patch('documents.views.DocumentAIService')
    def test_perfect_manual_upload(self, MockAIService, MockS3Service, MockWorkflowCreate):
        # This test simulates a perfect upload scenario where everything works as expected.
        
        # 1. Program our Mocks to return fake success data
        mock_s3_instance = MockS3Service.return_value
        mock_s3_instance.upload_file_bytes.return_value = "https://mock-s3-url.com/success.pdf"
        
        mock_ai_instance = MockAIService.return_value
        mock_ai_instance.generate_summary.return_value = "This is a brilliantly generated AI summary."

        # 2. Create a perfect, valid PDF file
        good_file = SimpleUploadedFile(
            "perfect_invoice.pdf", 
            b"perfect valid pdf content", 
            content_type="application/pdf"
        )

        # 3. Send the request!
        response = self.client.post(self.upload_url, {
            'file': good_file,
            'document_type_id': self.doc_type.id,
            'workflow_id': 'wf-789'
        }, format='multipart')

        # 4. Verify the success response
        self.assertEqual(response.status_code, 201)
        self.assertIn("Upload successful", response.data['message'])

        # 5. Verify the Database Chain Reaction happened perfectly (for your tables)
        self.assertEqual(Document.objects.count(), 1)
        saved_doc = Document.objects.first()
        self.assertEqual(saved_doc.document_name, "perfect_invoice.pdf")
        self.assertEqual(saved_doc.s3_url, "https://mock-s3-url.com/success.pdf")
        self.assertEqual(saved_doc.ai_summary, "This is a brilliantly generated AI summary.")
        self.assertEqual(ManualUploadDocument.objects.count(), 1)
        
        # 6. Verify the Handshake was ATTEMPTED with the correct data
        # Because we mocked it, we just check if your code tried to call it!
        MockWorkflowCreate.assert_called_once()
        
        # We can even check if it sent the right workflow_id
        called_args, called_kwargs = MockWorkflowCreate.call_args
        self.assertEqual(called_kwargs['workflow_id'], 'wf-789')