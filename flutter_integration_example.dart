// // Flutter Integration Example for Emotion Detection API
// // Copy this code to your Flutter project and adapt as needed

// import 'dart:convert';
// import 'dart:typed_data';
// import 'package:http/http.dart' as http;
// import 'package:http_parser/http_parser.dart';

// class EmotionDetectionService {
//   final String baseUrl;
//   final String? apiKey;  // Optional, only if server has API_KEY env var set
  
//   String? _currentSessionId;
  
//   EmotionDetectionService({
//     required this.baseUrl,  // e.g., "http://10.19.40.133:8000"
//     this.apiKey,
//   });
  
//   // Helper to add auth header if needed
//   Map<String, String> _getHeaders({Map<String, String>? additional}) {
//     final headers = <String, String>{};
//     if (apiKey != null) {
//       headers['x-api-key'] = apiKey!;
//     }
//     if (additional != null) {
//       headers.addAll(additional);
//     }
//     return headers;
//   }
  
//   // 1. Check server health
//   Future<bool> checkHealth() async {
//     try {
//       final response = await http.get(
//         Uri.parse('$baseUrl/health'),
//       );
      
//       if (response.statusCode == 200) {
//         final data = jsonDecode(response.body);
//         return data['status'] == 'healthy' && data['model_loaded'] == true;
//       }
//       return false;
//     } catch (e) {
//       print('Health check failed: $e');
//       return false;
//     }
//   }
  
//   // 2. Start interview session
//   Future<String?> startSession() async {
//     try {
//       final response = await http.post(
//         Uri.parse('$baseUrl/start_session'),
//         headers: _getHeaders(),
//       );
      
//       if (response.statusCode == 200) {
//         final data = jsonDecode(response.body);
//         _currentSessionId = data['session_id'];
//         print('✅ Session started: $_currentSessionId');
//         return _currentSessionId;
//       } else {
//         print('❌ Failed to start session: ${response.statusCode}');
//         print('Response: ${response.body}');
//         return null;
//       }
//     } catch (e) {
//       print('❌ Error starting session: $e');
//       return null;
//     }
//   }
  
//   // 3. Send frame for emotion detection
//   // CRITICAL: Field name MUST be "image" (not "file")
//   Future<Map<String, dynamic>?> sendFrame(Uint8List imageBytes) async {
//     if (_currentSessionId == null) {
//       print('❌ No active session. Call startSession() first.');
//       return null;
//     }
    
//     try {
//       // Create multipart request
//       var request = http.MultipartRequest(
//         'POST',
//         Uri.parse('$baseUrl/predict_frame'),
//       );
      
//       // Add headers
//       if (apiKey != null) {
//         request.headers['x-api-key'] = apiKey!;
//       }
      
//       // Add session ID as form field
//       request.fields['session_id'] = _currentSessionId!;
      
//       // Add image with field name "image" (NOT "file"!)
//       request.files.add(
//         http.MultipartFile.fromBytes(
//           'image',  // ⚠️ MUST BE "image"
//           imageBytes,
//           filename: 'frame.jpg',
//           contentType: MediaType('image', 'jpeg'),
//         ),
//       );
      
//       // Send request
//       final streamedResponse = await request.send();
//       final response = await http.Response.fromStream(streamedResponse);
      
//       if (response.statusCode == 200) {
//         final result = jsonDecode(response.body);
        
//         // Log result
//         if (result['faces_found'] > 0) {
//           final emotion = result['top_result']['emotion'];
//           final confidence = result['top_result']['confidence'];
//           print('😊 Detected: $emotion (${(confidence * 100).toStringAsFixed(1)}%)');
//         } else {
//           print('👤 No face detected in frame');
//         }
        
//         return result;
//       } else if (response.statusCode == 422) {
//         print('❌ Validation error (422)');
//         print('Make sure field name is "image" not "file"');
//         print('Response: ${response.body}');
//         return null;
//       } else {
//         print('❌ Failed to process frame: ${response.statusCode}');
//         print('Response: ${response.body}');
//         return null;
//       }
//     } catch (e) {
//       print('❌ Error sending frame: $e');
//       return null;
//     }
//   }
  
//   // 4. Stop session and get report
//   Future<Map<String, dynamic>?> stopSession() async {
//     if (_currentSessionId == null) {
//       print('❌ No active session to stop.');
//       return null;
//     }
    
//     try {
//       final response = await http.post(
//         Uri.parse('$baseUrl/stop_session'),
//         headers: _getHeaders(additional: {
//           'Content-Type': 'application/json',
//         }),
//         body: jsonEncode({
//           'session_id': _currentSessionId,
//         }),
//       );
      
//       if (response.statusCode == 200) {
//         final report = jsonDecode(response.body);
        
//         print('🛑 Session stopped');
//         print('📊 Duration: ${report['duration_seconds']}s');
//         print('📈 Frames processed: ${report['summary']['total_frames_processed']}');
//         print('😊 Emotions: ${report['emotion_counts']}');
        
//         if (report['summary']['dominant_emotions'].isNotEmpty) {
//           final dominant = report['summary']['dominant_emotions'][0];
//           print('🏆 Dominant: ${dominant['emotion']} (${dominant['percentage'].toStringAsFixed(1)}%)');
//         }
        
//         _currentSessionId = null;
//         return report;
//       } else {
//         print('❌ Failed to stop session: ${response.statusCode}');
//         print('Response: ${response.body}');
//         return null;
//       }
//     } catch (e) {
//       print('❌ Error stopping session: $e');
//       return null;
//     }
//   }
  
//   // 5. Reset session (optional, for debugging)
//   Future<bool> resetSession() async {
//     if (_currentSessionId == null) {
//       print('❌ No active session to reset.');
//       return false;
//     }
    
//     try {
//       final response = await http.post(
//         Uri.parse('$baseUrl/reset_session'),
//         headers: _getHeaders(additional: {
//           'Content-Type': 'application/json',
//         }),
//         body: jsonEncode({
//           'session_id': _currentSessionId,
//         }),
//       );
      
//       if (response.statusCode == 200) {
//         print('🔄 Session reset successfully');
//         return true;
//       } else {
//         print('❌ Failed to reset session: ${response.statusCode}');
//         return false;
//       }
//     } catch (e) {
//       print('❌ Error resetting session: $e');
//       return false;
//     }
//   }
  
//   // Helper: Decode base64 frames from report
//   List<Uint8List> getFramesForEmotion(Map<String, dynamic> report, String emotion) {
//     final frames = <Uint8List>[];
    
//     if (report['saved_frames'] != null && report['saved_frames'][emotion] != null) {
//       for (var frame in report['saved_frames'][emotion]) {
//         final imageData = base64Decode(frame['frame_base64']);
//         frames.add(imageData);
//       }
//     }
    
//     return frames;
//   }
// }


// // USAGE EXAMPLE IN YOUR FLUTTER APP:

// /*
// void main() async {
//   // 1. Create service instance
//   final emotionService = EmotionDetectionService(
//     baseUrl: 'http://10.19.40.133:8000',  // Use your laptop's IP
//     apiKey: null,  // Set to your API key if server requires it
//   );
  
//   // 2. Check server health
//   final isHealthy = await emotionService.checkHealth();
//   if (!isHealthy) {
//     print('Server not reachable!');
//     return;
//   }
  
//   // 3. Start session
//   final sessionId = await emotionService.startSession();
//   if (sessionId == null) {
//     print('Failed to start session!');
//     return;
//   }
  
//   // 4. Send frames periodically (e.g., from camera stream)
//   // Assume you have imageBytes from camera
//   Uint8List imageBytes = ...; // Get from camera
  
//   final result = await emotionService.sendFrame(imageBytes);
//   if (result != null && result['faces_found'] > 0) {
//     final emotion = result['top_result']['emotion'];
//     final confidence = result['top_result']['confidence'];
//     print('Current emotion: $emotion ($confidence)');
//   }
  
//   // 5. Stop session and get report
//   final report = await emotionService.stopSession();
//   if (report != null) {
//     // Display report to user
//     print('Interview complete!');
//     print('Dominant emotions: ${report['summary']['dominant_emotions']}');
    
//     // Get saved frames for a specific emotion
//     final happyFrames = emotionService.getFramesForEmotion(report, 'happy');
//     print('Captured ${happyFrames.length} happy moments');
//   }
// }
// */


// // INTEGRATION WITH CAMERA:

// /*
// import 'package:camera/camera.dart';

// class InterviewScreen extends StatefulWidget {
//   @override
//   _InterviewScreenState createState() => _InterviewScreenState();
// }

// class _InterviewScreenState extends State<InterviewScreen> {
//   CameraController? _cameraController;
//   EmotionDetectionService? _emotionService;
//   bool _isProcessing = false;
  
//   @override
//   void initState() {
//     super.initState();
//     _initializeCamera();
//     _emotionService = EmotionDetectionService(
//       baseUrl: 'http://10.19.40.133:8000',
//     );
//   }
  
//   Future<void> _initializeCamera() async {
//     final cameras = await availableCameras();
//     final frontCamera = cameras.firstWhere(
//       (camera) => camera.lensDirection == CameraLensDirection.front,
//     );
    
//     _cameraController = CameraController(
//       frontCamera,
//       ResolutionPreset.medium,
//     );
    
//     await _cameraController!.initialize();
//     setState(() {});
    
//     // Start capturing frames
//     _cameraController!.startImageStream((image) async {
//       if (!_isProcessing) {
//         _isProcessing = true;
//         await _processFrame(image);
//         _isProcessing = false;
//       }
//     });
//   }
  
//   Future<void> _processFrame(CameraImage image) async {
//     // Convert CameraImage to JPEG bytes
//     final bytes = await _convertImageToJpeg(image);
    
//     // Send to API
//     await _emotionService!.sendFrame(bytes);
//   }
  
//   Future<Uint8List> _convertImageToJpeg(CameraImage image) async {
//     // Implementation depends on your image processing library
//     // You might use image package or platform-specific code
//     // Return JPEG bytes
//   }
  
//   Future<void> _startInterview() async {
//     await _emotionService!.startSession();
//   }
  
//   Future<void> _stopInterview() async {
//     final report = await _emotionService!.stopSession();
//     // Navigate to results screen with report
//   }
// }
// */

