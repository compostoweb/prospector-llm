import LinkedInSearchPage from "./linkedin-search-page"

export const metadata = {
  title: "Busca LinkedIn — Prospector",
}

export default function Page() {
  return (
    <div className="-m-6 h-[calc(100vh)] overflow-hidden">
      <LinkedInSearchPage />
    </div>
  )
}
