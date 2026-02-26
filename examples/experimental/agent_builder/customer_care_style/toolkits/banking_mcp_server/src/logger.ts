import pino from 'pino';
const logger = pino({
  level: process.env.LOG_LEVEL || 'info',
  transport: {
    target: 'pino-pretty',
    options: {
      colorize: true,
      translateTime: 'SYS:standard',
      ignore: 'pid,hostname',
    },
  },
});

/**
 * Log an informational message
 */
export function info(message: string, data?: any): void {
  if (data) {
    logger.info(data, message);
  } else {
    logger.info(message);
  }
}

/**
 * Log a warning message
 */
export function warn(message: string, data?: any): void {
  if (data) {
    logger.warn(data, message);
  } else {
    logger.warn(message);
  }
}

/**
 * Log an error message
 */
export function error(message: string, data?: any): void {
  if (data) {
    logger.error(data, message);
  } else {
    logger.error(message);
  }
}

/**
 * Default export with all logging methods
 */
export default {
  info,
  warn,
  error,
};