import Link from "next/link";
import BrandMark from "../../components/BrandMark";
import SignupForm from "./SignupForm";
import styles from "./signup.module.css";
export const metadata = { title: "Conheça o RotaPay para sua loja" };
export default function SignupPage(){return <main className={styles.page}><div className={styles.shell}><section className={styles.intro}><div className={styles.brand}><BrandMark size={40}/><span>RotaPay</span></div><h1>Veja se o RotaPay faz sentido para sua operação.</h1><p>Conte como sua loja vende, cobra e acerta com fornecedores. Nossa equipe analisa o perfil e entra em contato.</p></section><section className={styles.card} aria-labelledby="cadastro-titulo"><h2 id="cadastro-titulo">Solicite uma avaliação</h2><p className={styles.description}>Este formulário não cria uma conta nem solicita senha.</p><SignupForm/><p className={styles.footer}>Já possui acesso? <Link href="/login">Entrar no sistema</Link></p></section></div></main>}
