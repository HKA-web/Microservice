import { Router } from "express";
import { sendMessage } from "./services/sendmessage.js";
import { sendVideo } from "./services/sendvideo.js";
import { sendImage } from "./services/sendimage.js";
import { sendAudio } from "./services/sendaudio.js";
import { sendDocument } from "./services/senddocument.js";
import { checkRegistered } from "../middlewares/registered.js";

const router = Router();

router.post('/send-message', sendMessage);
router.post('/send-video', sendVideo);
router.post('/send-image', sendImage);
router.post('/send-audio', sendAudio);
router.post('/send-document', sendDocument);

export default router;
