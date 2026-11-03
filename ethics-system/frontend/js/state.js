// 전역 상태(로그인 사용자, 메타정보)
export const state = { user: null, meta: null };
export const canEdit = () => state.user && (state.user.role === 'admin' || state.user.role === 'staff');
export const isAdmin = () => state.user && state.user.role === 'admin';
export const STATUS_FLOW = ['RECEIVED', 'REVIEW', 'PENDING_APPROVAL', 'EXPLANATION_REQUESTED', 'EXPLANATION_REVIEW', 'COMMITTEE', 'CORRECTION_ORDERED', 'DISCIPLINE', 'CLOSED'];
export const COMMITTEES = { AD_REVIEW: '광고심사위원회', ETHICS: '윤리위원회', DISCIPLINE: '징계위원회', STANDING_BOARD: '상임이사회' };
